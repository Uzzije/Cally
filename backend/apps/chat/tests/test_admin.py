from django.contrib import admin
from django.test import TestCase

from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_turn import ChatTurn
from apps.chat.models.message import Message


class ChatAdminTests(TestCase):
    def test_chat_models_are_registered_for_admin_auditability(self):
        self.assertIn(ChatSession, admin.site._registry)
        self.assertIn(Message, admin.site._registry)
        self.assertIn(ChatTurn, admin.site._registry)

    def test_chat_turn_admin_marks_trace_fields_read_only(self):
        admin_config = admin.site._registry[ChatTurn]

        self.assertIn("trace_events", admin_config.readonly_fields)
        self.assertIn("eval_snapshot", admin_config.readonly_fields)
