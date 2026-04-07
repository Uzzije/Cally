from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models.chat_session import ChatSession
from apps.chat.services.chat_content_block_validation_service import ChatContentBlockValidationError
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

        tool_calls = message.tool_calls
        if tool_calls is None:
            self.fail("Expected tool_calls to be persisted")
        self.assertEqual(tool_calls[0]["tool_name"], "get_events")

    def test_serialize_history_renders_textual_blocks(self):
        self.service.create_user_message(self.session, content="When is my next meeting?")
        self.service.create_assistant_message(
            self.session,
            content_blocks=[{"type": "clarification", "text": "Do you mean today or tomorrow?"}],
        )

        history = self.service.serialize_history(self.session)

        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["content"], "Do you mean today or tomorrow?")

    def test_serialize_history_can_limit_to_recent_messages(self):
        self.service.create_user_message(self.session, content="First")
        self.service.create_assistant_message(
            self.session,
            content_blocks=[{"type": "text", "text": "Second"}],
        )
        self.service.create_user_message(self.session, content="Third")

        history = self.service.serialize_history(self.session, limit=2)

        self.assertEqual([item["content"] for item in history], ["Second", "Third"])

    def test_create_assistant_message_rejects_malformed_action_card_blocks(self):
        with self.assertRaises(ChatContentBlockValidationError):
            self.service.create_assistant_message(
                self.session,
                content_blocks=[
                    {
                        "type": "action_card",
                        "actions": [
                            {
                                "id": "proposal-1",
                                "action_type": "create_event",
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

    def test_create_assistant_message_accepts_ranked_action_card_details(self):
        message = self.service.create_assistant_message(
            self.session,
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
                                "rank": 1,
                                "why": "Protects your blocked-time focus windows.",
                            },
                            "status": "pending",
                        }
                    ],
                }
            ],
        )

        self.assertEqual(message.content_blocks[0]["actions"][0]["details"]["rank"], 1)

    def test_create_assistant_message_accepts_email_draft_blocks(self):
        message = self.service.create_assistant_message(
            self.session,
            content_blocks=[
                {
                    "type": "email_draft",
                    "to": ["joe@example.com"],
                    "cc": [],
                    "subject": "Quick sync this week?",
                    "body": "Hi Joe,\n\nCould we find 30 minutes this week?\n",
                    "status": "draft",
                    "status_detail": "Draft only. Not sent.",
                }
            ],
        )

        self.assertEqual(message.content_blocks[0]["type"], "email_draft")
        self.assertEqual(message.content_blocks[0]["subject"], "Quick sync this week?")

    def test_serialize_history_renders_email_draft_as_textual_summary(self):
        self.service.create_assistant_message(
            self.session,
            content_blocks=[
                {
                    "type": "email_draft",
                    "to": ["joe@example.com"],
                    "cc": ["manager@example.com"],
                    "subject": "Quick sync this week?",
                    "body": "Hi Joe,\n\nCould we find 30 minutes this week?\n",
                    "status": "draft",
                    "status_detail": "Draft only. Not sent.",
                }
            ],
        )

        history = self.service.serialize_history(self.session)

        self.assertEqual(
            history[0]["content"],
            (
                "Email draft\n"
                "To: joe@example.com\n"
                "Cc: manager@example.com\n"
                "Subject: Quick sync this week?\n\n"
                "Hi Joe,\n\nCould we find 30 minutes this week?"
            ),
        )

    def test_create_assistant_message_accepts_chart_blocks(self):
        message = self.service.create_assistant_message(
            self.session,
            content_blocks=[
                {
                    "type": "chart",
                    "chart_type": "bar",
                    "title": "Meeting hours this week",
                    "data": [
                        {"label": "Mon", "value": 4},
                        {"label": "Tue", "value": 2},
                    ],
                    "save_enabled": True,
                }
            ],
        )

        self.assertEqual(message.content_blocks[0]["type"], "chart")
        self.assertEqual(message.content_blocks[0]["title"], "Meeting hours this week")

    def test_serialize_history_renders_chart_as_textual_summary(self):
        self.service.create_assistant_message(
            self.session,
            content_blocks=[
                {
                    "type": "chart",
                    "chart_type": "bar",
                    "title": "Meeting hours this week",
                    "data": [
                        {"label": "Mon", "value": 4},
                        {"label": "Tue", "value": 2},
                        {"label": "Wed", "value": 1},
                    ],
                    "save_enabled": True,
                }
            ],
        )

        history = self.service.serialize_history(self.session)

        self.assertEqual(
            history[0]["content"],
            "Chart (bar): Meeting hours this week\nMon: 4, Tue: 2, Wed: 1",
        )
