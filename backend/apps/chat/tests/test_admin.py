from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.client import RequestFactory

from apps.chat.models.chat_rate_limit_config import ChatRateLimitConfig
from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_turn import ChatTurn
from apps.chat.models.message import Message

User = get_user_model()


class ChatAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User.objects.create_superuser(
            username="chat-admin",
            email="chat-admin@example.com",
            password="test-pass-123",
        )

    def test_chat_models_are_registered_for_admin_auditability(self):
        self.assertIn(ChatSession, admin.site._registry)
        self.assertIn(Message, admin.site._registry)
        self.assertIn(ChatTurn, admin.site._registry)
        self.assertIn(ChatRateLimitConfig, admin.site._registry)

    def test_chat_turn_admin_marks_trace_fields_read_only(self):
        admin_config = admin.site._registry[ChatTurn]

        self.assertIn("trace_events", admin_config.readonly_fields)
        self.assertIn("eval_snapshot", admin_config.readonly_fields)

    def test_chat_rate_limit_config_admin_enforces_singleton_behavior(self):
        admin_config = admin.site._registry[ChatRateLimitConfig]
        request = self.factory.get("/admin/chat/chatratelimitconfig/")
        request.user = self.admin_user

        self.assertTrue(admin_config.has_add_permission(request))
        self.assertFalse(admin_config.has_delete_permission(request))

        config = ChatRateLimitConfig.objects.create(
            singleton_key="default",
            daily_message_credit_limit=25,
        )

        self.assertFalse(admin_config.has_add_permission(request))
        self.assertIn("singleton_key", admin_config.get_readonly_fields(request, obj=config))
