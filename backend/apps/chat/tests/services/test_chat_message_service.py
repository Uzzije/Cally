from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models.chat_session import ChatSession
from apps.chat.services.chat_message_service import ChatMessageService
from apps.core_agent.models.tool_execution_result import ToolExecutionResult


User = get_user_model()


class ChatMessageServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="chat-message-service@example.com",
            password="test-pass-123",
        )
        self.session = ChatSession.objects.create(user=self.user)
        self.service = ChatMessageService()

    def test_create_user_message_persists_text_block(self):
        message = self.service.create_user_message(
            self.session,
            content="What does tomorrow look like?",
        )

        self.assertEqual(message.content_blocks[0]["text"], "What does tomorrow look like?")

    def test_create_assistant_message_persists_tool_calls(self):
        message = self.service.create_assistant_message(
            self.session,
            content_blocks=[{"type": "text", "text": "You have one meeting tomorrow."}],
            tool_calls=[
                ToolExecutionResult(
                    tool_name="get_events",
                    tool_args={"start": "2026-04-06T00:00:00+00:00"},
                    result="[]",
                )
            ],
        )

        self.assertEqual(message.tool_calls[0]["tool_name"], "get_events")

    def test_serialize_history_renders_textual_blocks(self):
        self.service.create_user_message(self.session, content="When is my next meeting?")
        self.service.create_assistant_message(
            self.session,
            content_blocks=[{"type": "clarification", "text": "Do you mean today or tomorrow?"}],
        )

        history = self.service.serialize_history(self.session)

        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["content"], "Do you mean today or tomorrow?")

