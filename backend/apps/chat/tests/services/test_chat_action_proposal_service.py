from __future__ import annotations

from typing import Any, cast
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models.action_execution import ActionExecution
from apps.chat.models.action_proposal import ActionProposal, ActionProposalStatus
from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_turn import ChatTurn
from apps.chat.models.message import Message, MessageRole
from apps.chat.services.chat_action_proposal_service import (
    ActionProposalConflictError,
    ActionProposalPayloadError,
    ActionProposalPolicyError,
    ChatActionProposalService,
)
from apps.chat.services.chat_execution_policy_service import ExecutionPolicyDecision

User = get_user_model()


class ChatActionProposalServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="proposal-owner",
            email="proposal-owner@example.com",
            password="test-pass-123",
        )
        self.session = ChatSession.objects.create(user=self.user)
        self.user_message = Message.objects.create(
            session=self.session,
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "Schedule a meeting"}],
        )
        self.turn = ChatTurn.objects.create(
            session=self.session,
            user_message=self.user_message,
            correlation_id="corr-proposal-service",
        )
        self.assistant_message = Message.objects.create(
            session=self.session,
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
                            "payload": {
                                "title": "Meeting with Joe",
                                "start_time": "2026-04-07T13:00:00+00:00",
                                "end_time": "2026-04-07T13:30:00+00:00",
                                "timezone": "America/New_York",
                                "attendees": ["joe@example.com"],
                            },
                            "status": "pending",
                        }
                    ],
                }
            ],
        )
        self.service = ChatActionProposalService(
            execution_policy_service=Mock(),
            calendar_event_mutation_service=Mock(),
        )

    def test_persist_from_message_creates_proposals_and_rewrites_message_ids(self):
        proposals = self.service.persist_from_message(
            session=self.session,
            turn=self.turn,
            assistant_message=self.assistant_message,
        )

        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        self.assertTrue(ActionProposal.objects.filter(public_id=proposal.public_id).exists())
        self.assistant_message.refresh_from_db()
        action = self.assistant_message.content_blocks[0]["actions"][0]
        self.assertEqual(action["id"], proposal.public_id)
        self.assertNotIn("payload", action)

    def test_reject_proposal_marks_status_and_does_not_execute(self):
        proposal = self.service.persist_from_message(
            session=self.session,
            turn=self.turn,
            assistant_message=self.assistant_message,
        )[0]

        rejected = self.service.reject_proposal(
            self.user,
            session_id=self.session.id,
            proposal_id=proposal.public_id,
        )

        self.assertEqual(rejected.status, ActionProposalStatus.REJECTED)
        self.assertEqual(rejected.status_detail, "Rejected. No calendar changes were made.")
        self.assertEqual(ActionExecution.objects.count(), 0)
        self.assistant_message.refresh_from_db()
        self.assertEqual(
            self.assistant_message.content_blocks[0]["actions"][0]["status"],
            ActionProposalStatus.REJECTED,
        )

    def test_approve_proposal_executes_and_records_result(self):
        proposal = self.service.persist_from_message(
            session=self.session,
            turn=self.turn,
            assistant_message=self.assistant_message,
        )[0]
        cast(Any, self.service.execution_policy_service).evaluate.return_value = (
            ExecutionPolicyDecision(allowed=True)
        )
        cast(
            Any, self.service.calendar_event_mutation_service
        ).create_primary_calendar_event.return_value = Mock(
            event_id=33,
            google_event_id="google-event-33",
        )

        approved = self.service.approve_proposal(
            self.user,
            session_id=self.session.id,
            proposal_id=proposal.public_id,
        )

        self.assertEqual(approved.status, ActionProposalStatus.EXECUTED)
        self.assertEqual(approved.result_payload["event_id"], 33)
        execution = ActionExecution.objects.get(proposal=proposal)
        self.assertEqual(execution.status, "executed")
        self.assistant_message.refresh_from_db()
        action = self.assistant_message.content_blocks[0]["actions"][0]
        self.assertEqual(action["status"], ActionProposalStatus.EXECUTED)
        self.assertEqual(action["result"]["google_event_id"], "google-event-33")

    def test_approve_proposal_fails_closed_when_policy_blocks_execution(self):
        proposal = self.service.persist_from_message(
            session=self.session,
            turn=self.turn,
            assistant_message=self.assistant_message,
        )[0]
        cast(Any, self.service.execution_policy_service).evaluate.return_value = (
            ExecutionPolicyDecision(
                allowed=False,
                reason="Draft-only mode keeps this proposal review-only.",
            )
        )

        with self.assertRaises(ActionProposalPolicyError):
            self.service.approve_proposal(
                self.user,
                session_id=self.session.id,
                proposal_id=proposal.public_id,
            )

        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ActionProposalStatus.PENDING)
        self.assertEqual(ActionExecution.objects.count(), 0)

    def test_approve_proposal_raises_domain_error_when_execution_payload_is_missing(self):
        self.assistant_message.content_blocks[0]["actions"][0].pop("payload")
        self.assistant_message.save(update_fields=["content_blocks"])
        proposal = self.service.persist_from_message(
            session=self.session,
            turn=self.turn,
            assistant_message=self.assistant_message,
        )[0]
        cast(Any, self.service.execution_policy_service).evaluate.return_value = (
            ExecutionPolicyDecision(allowed=True)
        )

        with self.assertRaises(ActionProposalPayloadError):
            self.service.approve_proposal(
                self.user,
                session_id=self.session.id,
                proposal_id=proposal.public_id,
            )

        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ActionProposalStatus.PENDING)

    def test_reject_requires_pending_status(self):
        proposal = self.service.persist_from_message(
            session=self.session,
            turn=self.turn,
            assistant_message=self.assistant_message,
        )[0]
        proposal.status = ActionProposalStatus.EXECUTED
        proposal.save(update_fields=["status"])

        with self.assertRaises(ActionProposalConflictError):
            self.service.reject_proposal(
                self.user,
                session_id=self.session.id,
                proposal_id=proposal.public_id,
            )
