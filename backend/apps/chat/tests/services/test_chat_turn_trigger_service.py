from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_turn import ChatTurn
from apps.chat.models.message import Message, MessageRole
from apps.chat.services.chat_turn_trigger_service import ChatTurnTriggerService

User = get_user_model()


class ChatTurnTriggerServiceTests(TestCase):
    def test_publishes_chat_turn_requested_event(self):
        user = User.objects.create_user(
            username="ignored",
            email="chat-turn-trigger@example.com",
            password="test-pass-123",
        )
        session = ChatSession.objects.create(user=user)
        user_message = Message.objects.create(
            session=session,
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "What does tomorrow look like?"}],
        )
        turn = ChatTurn.objects.create(
            session=session,
            user_message=user_message,
            correlation_id="corr-123",
        )
        client = Mock()
        client.send_sync.return_value = ["evt-1"]

        event_ids = ChatTurnTriggerService(client=client).request_turn_processing(turn=turn)

        self.assertEqual(event_ids, ["evt-1"])
        client.send_sync.assert_called_once()
        sent_event = client.send_sync.call_args.args[0]
        self.assertEqual(sent_event.name, "chat.turn.requested")
        self.assertEqual(sent_event.data["turn_id"], turn.id)
        self.assertEqual(sent_event.data["session_id"], session.id)
        self.assertEqual(sent_event.data["user_id"], user.id)
