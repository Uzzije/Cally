from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models.chat_session import ChatSession


User = get_user_model()


class ChatSessionModelTests(TestCase):
    def test_defaults_title_to_new_conversation(self):
        user = User.objects.create_user(
            username="ignored",
            email="chat-session@example.com",
            password="test-pass-123",
        )

        session = ChatSession.objects.create(user=user)

        self.assertEqual(session.title, "New conversation")

