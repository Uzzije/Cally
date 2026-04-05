from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.services.chat_session_service import ChatSessionService


User = get_user_model()


class ChatSessionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="chat-service@example.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="ignored-other",
            email="chat-service-other@example.com",
            password="test-pass-123",
        )
        self.service = ChatSessionService()

    def test_create_session_creates_new_conversation_by_default(self):
        session = self.service.create_session(self.user)

        self.assertEqual(session.title, "New conversation")

    def test_list_sessions_returns_only_owned_sessions(self):
        owned_session = self.service.create_session(self.user)
        self.service.create_session(self.other_user)

        sessions = list(self.service.list_sessions(self.user))

        self.assertEqual([session.id for session in sessions], [owned_session.id])

    def test_assign_title_from_first_message_updates_default_title(self):
        session = self.service.create_session(self.user)

        self.service.assign_title_from_message(
            session,
            message_text="What does tomorrow look like for my calendar?",
        )

        session.refresh_from_db()
        self.assertEqual(session.title, "What does tomorrow look like for my calendar?")
