from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models.chat_session import ChatSession
from apps.core_agent.models.agent_turn_result import AgentTurnResult
from apps.core_agent.models.tool_execution_result import ToolExecutionResult


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

    def test_get_messages_blocks_cross_user_access(self):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.other_user)

        response = self.client.get(
            f"/api/v1/chat/sessions/{session.id}/messages",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 404)

    @patch("apps.bff.api.routers.chat_router.ChatAssistantTurnService")
    def test_post_message_persists_user_and_assistant_messages(self, assistant_service_class):
        self.client.force_login(self.user)
        session = ChatSession.objects.create(user=self.user)
        assistant_service_class.return_value.generate_response.return_value = AgentTurnResult(
            kind="answer",
            text="You have one meeting tomorrow.",
            tool_calls=[
                ToolExecutionResult(
                    tool_name="get_events",
                    tool_args={"start": "2026-04-06T00:00:00+00:00"},
                    result="[]",
                )
            ],
        )
        assistant_service_class.return_value.build_content_blocks.return_value = [
            {"type": "text", "text": "You have one meeting tomorrow."}
        ]

        response = self.client.post(
            f"/api/v1/chat/sessions/{session.id}/messages",
            data='{"content": "What does tomorrow look like?"}',
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user_message"]["role"], "user")
        self.assertEqual(payload["assistant_message"]["content_blocks"][0]["text"], "You have one meeting tomorrow.")

