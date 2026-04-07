from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models.action_proposal import ActionProposal, ActionProposalStatus
from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_rate_limit_config import ChatRateLimitConfig
from apps.chat.models.chat_turn import (
    ChatTurn,
    ChatTurnResultKind,
    ChatTurnScopeDecision,
    ChatTurnStatus,
)
from apps.chat.models.daily_message_credit_usage import DailyMessageCreditUsage
from apps.chat.models.message import MessageRole
from apps.chat.services.chat_action_proposal_service import (
    ActionProposalPayloadError,
    ActionProposalPolicyError,
)

User = get_user_model()


class ChatRouterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="chat-router@example.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="ignored-other",
            email="chat-router-other@example.com",
            password="test-pass-123",
        )

    def test_list_sessions_requires_authentication(self):
        response = self.client.get("/api/v1/chat/sessions", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 401)

    def test_create_session_returns_new_session(self):
        self.client.force_login(self.user)

        response = self.client.post("/api/v1/chat/sessions", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "New conversation")

    def test_get_chat_credits_returns_default_daily_balance(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/chat/credits", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["limit"], 10)
        self.assertEqual(response.json()["used"], 0)
        self.assertEqual(response.json()["remaining"], 10)

    def test_get_messages_blocks_cross_user_access(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.other_user)

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/messages",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 404)

    @patch("apps.bff.api.routers.chat_router.ChatTurnTriggerService")
    def test_post_message_returns_accepted_turn_payload(self, trigger_service_class):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        trigger_service_class.return_value.request_turn_processing.return_value = ["evt-1"]

        response = self.client.post(
            f"/api/v1/chat/sessions/{session.id}/messages",
            data='{"content": "What does tomorrow look like?"}',
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["user_message"]["role"], "user")
        self.assertEqual(payload["turn"]["status"], "queued")
        self.assertTrue(ChatTurn.objects.filter(session=session).exists())
        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            DailyMessageCreditUsage.objects.get(user=self.user).used_credits,
            1,
        )

    @patch("apps.bff.api.routers.chat_router.ChatTurnTriggerService")
    def test_post_message_returns_rate_limit_error_when_daily_credits_are_exhausted(
        self, trigger_service_class
    ):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        ChatRateLimitConfig.objects.create(singleton_key="default", daily_message_credit_limit=1)
        DailyMessageCreditUsage.objects.create(
            user=self.user,
            usage_date=session.created_at.date(),
            used_credits=1,
        )

        response = self.client.post(
            f"/api/v1/chat/sessions/{session.id}/messages",
            data='{"content": "What does tomorrow look like?"}',
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            response.json(),
            {"detail": "You have used all 1 AI message credits for today."},
        )
        self.assertFalse(ChatTurn.objects.filter(session=session).exists())
        trigger_service_class.return_value.request_turn_processing.assert_not_called()

    def test_poll_turn_blocks_cross_user_access(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.other_user)
        user_message = session.messages.create(
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "What does tomorrow look like?"}],
        )
        turn = ChatTurn.objects.create(
            session=session,
            user_message=user_message,
            correlation_id="corr-unauthorized",
        )

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/turns/{turn.id}",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 404)

    def test_poll_turn_returns_assistant_message_when_completed(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        user_message = session.messages.create(
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "What does tomorrow look like?"}],
        )
        assistant_message = session.messages.create(
            role=MessageRole.ASSISTANT,
            content_blocks=[{"type": "text", "text": "You have one meeting tomorrow."}],
        )
        turn = ChatTurn.objects.create(
            session=session,
            user_message=user_message,
            assistant_message=assistant_message,
            correlation_id="corr-completed",
            status=ChatTurnStatus.COMPLETED,
            result_kind=ChatTurnResultKind.ANSWER,
            scope_decision=ChatTurnScopeDecision.IN_SCOPE,
        )

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/turns/{turn.id}",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["turn"]["status"], "completed")
        self.assertIsInstance(payload["turn"]["trace_events"], list)
        self.assertEqual(
            payload["assistant_message"]["content_blocks"][0]["text"],
            "You have one meeting tomorrow.",
        )

    def test_poll_turn_returns_action_card_assistant_message_when_completed(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        user_message = session.messages.create(
            role=MessageRole.USER,
            content_blocks=[
                {"type": "text", "text": "Schedule a 30 minute meeting with Joe tomorrow"}
            ],
        )
        assistant_message = session.messages.create(
            role=MessageRole.ASSISTANT,
            content_blocks=[
                {
                    "type": "action_card",
                    "actions": [
                        {
                            "id": "proposal-1",
                            "action_type": "create_event",
                            "summary": "Meeting with Joe",
                            "details": {
                                "date": "Tue Apr 7",
                                "time": "9:00 AM-9:30 AM",
                                "attendees": ["Joe"],
                            },
                            "status": "pending",
                        }
                    ],
                }
            ],
        )
        turn = ChatTurn.objects.create(
            session=session,
            user_message=user_message,
            assistant_message=assistant_message,
            correlation_id="corr-proposal-completed",
            status=ChatTurnStatus.COMPLETED,
            result_kind=ChatTurnResultKind.ANSWER,
            scope_decision=ChatTurnScopeDecision.IN_SCOPE,
        )

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/turns/{turn.id}",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["assistant_message"]["content_blocks"][0]["type"], "action_card")
        self.assertEqual(
            payload["assistant_message"]["content_blocks"][0]["actions"][0]["summary"],
            "Meeting with Joe",
        )

    def test_poll_turn_returns_email_draft_assistant_message_when_completed(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        user_message = session.messages.create(
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "Draft an email to Joe about tomorrow"}],
        )
        assistant_message = session.messages.create(
            role=MessageRole.ASSISTANT,
            content_blocks=[
                {
                    "type": "email_draft",
                    "to": ["joe@example.com"],
                    "cc": [],
                    "subject": "Tomorrow afternoon",
                    "body": "Hi Joe,\n\nWould tomorrow afternoon work for you?\n",
                    "status": "draft",
                    "status_detail": "Draft only. Not sent.",
                }
            ],
        )
        turn = ChatTurn.objects.create(
            session=session,
            user_message=user_message,
            assistant_message=assistant_message,
            correlation_id="corr-draft-completed",
            status=ChatTurnStatus.COMPLETED,
            result_kind=ChatTurnResultKind.ANSWER,
            scope_decision=ChatTurnScopeDecision.IN_SCOPE,
        )

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/turns/{turn.id}",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["assistant_message"]["content_blocks"][0]["type"], "email_draft")
        self.assertEqual(
            payload["assistant_message"]["content_blocks"][0]["subject"], "Tomorrow afternoon"
        )

    def test_poll_turn_returns_failed_state_without_cross_session_leak(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        user_message = session.messages.create(
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "What does tomorrow look like?"}],
        )
        turn = ChatTurn.objects.create(
            session=session,
            user_message=user_message,
            correlation_id="corr-failed",
            status=ChatTurnStatus.FAILED,
            result_kind=ChatTurnResultKind.ERROR,
            scope_decision=ChatTurnScopeDecision.IN_SCOPE,
            failure_reason="provider_error",
        )

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/turns/{turn.id}",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["turn"]["status"], "failed")
        self.assertEqual(payload["turn"]["failure_reason"], "provider_error")

    def test_get_messages_returns_action_card_blocks(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        session.messages.create(
            role=MessageRole.ASSISTANT,
            content_blocks=[
                {
                    "type": "action_card",
                    "actions": [
                        {
                            "id": "proposal-1",
                            "action_type": "create_event",
                            "summary": "Meeting with Joe",
                            "details": {
                                "date": "Tue Apr 7",
                                "time": "9:00 AM-9:30 AM",
                                "attendees": ["Joe"],
                            },
                            "status": "pending",
                        }
                    ],
                }
            ],
        )

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/messages",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["messages"][0]["content_blocks"][0]["type"], "action_card")
        self.assertEqual(
            payload["messages"][0]["content_blocks"][0]["actions"][0]["summary"],
            "Meeting with Joe",
        )

    def test_get_messages_returns_email_draft_blocks(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        session.messages.create(
            role=MessageRole.ASSISTANT,
            content_blocks=[
                {
                    "type": "email_draft",
                    "to": ["joe@example.com"],
                    "cc": [],
                    "subject": "Tomorrow afternoon",
                    "body": "Hi Joe,\n\nWould tomorrow afternoon work for you?\n",
                    "status": "draft",
                    "status_detail": "Draft only. Not sent.",
                }
            ],
        )

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/messages",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["messages"][0]["content_blocks"][0]["type"], "email_draft")
        self.assertEqual(payload["messages"][0]["content_blocks"][0]["to"], ["joe@example.com"])

    @patch("apps.bff.api.routers.chat_router.ChatActionProposalService")
    def test_approve_proposal_returns_conflict_when_payload_is_missing(
        self, proposal_service_class
    ):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        proposal_service_class.return_value.approve_proposal.side_effect = (
            ActionProposalPayloadError(
                "This proposal is missing execution details. Please ask me to draft it again."
            )
        )

        response = self.client.post(
            f"/api/v1/chat/sessions/{session.id}/proposals/proposal-1/approve",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("missing execution details", response.json()["detail"])

    def test_get_proposal_returns_latest_status_for_owner(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        user_message = session.messages.create(
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "Schedule a meeting"}],
        )
        assistant_message = session.messages.create(
            role=MessageRole.ASSISTANT,
            content_blocks=[{"type": "action_card", "actions": []}],
        )
        turn = ChatTurn.objects.create(
            session=session,
            user_message=user_message,
            assistant_message=assistant_message,
            correlation_id="corr-proposal-status",
        )
        proposal = ActionProposal.objects.create(
            session=session,
            turn=turn,
            assistant_message=assistant_message,
            public_id="proposal-public-id",
            action_type="create_event",
            summary="Meeting with Joe",
            details={"date": "Tue Apr 7", "time": "9:00 AM-9:30 AM", "attendees": ["Joe"]},
            status=ActionProposalStatus.EXECUTED,
            result_payload={"event_id": 8, "google_event_id": "google-event-8"},
        )

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/proposals/{proposal.public_id}",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "executed")
        self.assertEqual(payload["result"]["google_event_id"], "google-event-8")

    @patch("apps.bff.api.routers.chat_router.ChatActionProposalService")
    def test_approve_proposal_returns_conflict_when_policy_blocks_execution(
        self, proposal_service_class
    ):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        proposal_service_class.return_value.approve_proposal.side_effect = (
            ActionProposalPolicyError("Draft-only mode keeps this proposal review-only.")
        )

        response = self.client.post(
            f"/api/v1/chat/sessions/{session.id}/proposals/proposal-1/approve",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("Draft-only mode", response.json()["detail"])

    @patch("apps.bff.api.routers.chat_router.ChatActionProposalService")
    def test_reject_proposal_returns_updated_state(self, proposal_service_class):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        assistant_message = session.messages.create(
            role=MessageRole.ASSISTANT,
            content_blocks=[{"type": "action_card", "actions": []}],
        )
        user_message = session.messages.create(
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "Schedule a meeting"}],
        )
        turn = ChatTurn.objects.create(
            session=session,
            user_message=user_message,
            assistant_message=assistant_message,
            correlation_id="corr-reject-proposal",
        )
        proposal = ActionProposal.objects.create(
            session=session,
            turn=turn,
            assistant_message=assistant_message,
            public_id="proposal-1",
            action_type="create_event",
            summary="Meeting with Joe",
            details={"date": "Tue Apr 7", "time": "9:00 AM-9:30 AM", "attendees": ["Joe"]},
            status=ActionProposalStatus.REJECTED,
            status_detail="Rejected. No calendar changes were made.",
        )
        proposal_service_class.return_value.reject_proposal.return_value = proposal

        response = self.client.post(
            f"/api/v1/chat/sessions/{session.id}/proposals/{proposal.public_id}/reject",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "rejected")
        self.assertIn("No calendar changes", payload["status_detail"])
