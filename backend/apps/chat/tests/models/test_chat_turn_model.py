from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_turn import (
    ChatTurn,
    ChatTurnResultKind,
    ChatTurnScopeDecision,
    ChatTurnStatus,
)
from apps.chat.models.message import Message, MessageRole

User = get_user_model()


class ChatTurnModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="chat-turn-model@example.com",
            password="test-pass-123",
        )
        self.session = ChatSession.objects.create(user=self.user)
        self.user_message = Message.objects.create(
            session=self.session,
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "What does tomorrow look like?"}],
        )

    def test_defaults_to_queued_with_empty_trace_and_eval_snapshot(self):
        turn = ChatTurn.objects.create(
            session=self.session,
            user_message=self.user_message,
            correlation_id="corr-123",
        )

        self.assertEqual(turn.status, ChatTurnStatus.QUEUED)
        self.assertEqual(turn.result_kind, ChatTurnResultKind.ERROR)
        self.assertEqual(turn.scope_decision, ChatTurnScopeDecision.AMBIGUOUS)
        self.assertEqual(turn.trace_events, [])
        self.assertEqual(turn.eval_snapshot, {})

    def test_can_link_assistant_message_and_structured_trace(self):
        assistant_message = Message.objects.create(
            session=self.session,
            role=MessageRole.ASSISTANT,
            content_blocks=[{"type": "text", "text": "You have a meeting tomorrow."}],
        )

        turn = ChatTurn.objects.create(
            session=self.session,
            user_message=self.user_message,
            assistant_message=assistant_message,
            correlation_id="corr-456",
            status=ChatTurnStatus.COMPLETED,
            result_kind=ChatTurnResultKind.ANSWER,
            scope_decision=ChatTurnScopeDecision.IN_SCOPE,
            trace_events=[
                {
                    "type": "turn_completed",
                    "timestamp": "2026-04-05T00:00:00+00:00",
                    "summary": "Completed turn",
                    "data": {"provider_called": True},
                }
            ],
            eval_snapshot={
                "user_prompt": "What does tomorrow look like?",
                "assistant_kind": "answer",
            },
        )

        self.assertEqual(turn.assistant_message_id, assistant_message.id)
        self.assertEqual(turn.trace_events[0]["type"], "turn_completed")
        self.assertEqual(turn.eval_snapshot["assistant_kind"], "answer")
