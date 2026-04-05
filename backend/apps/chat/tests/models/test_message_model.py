from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models.chat_session import ChatSession
from apps.chat.models.message import Message, MessageRole


User = get_user_model()


class MessageModelTests(TestCase):
    def test_message_persists_content_blocks(self):
        user = User.objects.create_user(
            username="ignored",
            email="message-model@example.com",
            password="test-pass-123",
        )
        session = ChatSession.objects.create(user=user)

        message = Message.objects.create(
            session=session,
            role=MessageRole.USER,
            content_blocks=[{"type": "text", "text": "What does tomorrow look like?"}],
        )

        self.assertEqual(message.content_blocks[0]["type"], "text")

