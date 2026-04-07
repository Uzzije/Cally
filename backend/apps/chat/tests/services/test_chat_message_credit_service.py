from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.chat.models.chat_rate_limit_config import ChatRateLimitConfig
from apps.chat.models.daily_message_credit_usage import DailyMessageCreditUsage
from apps.chat.services.chat_message_credit_service import (
    ChatMessageCreditLimitExceededError,
    ChatMessageCreditService,
)

User = get_user_model()


class ChatMessageCreditServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="credit-user",
            email="credits@example.com",
            password="test-pass-123",
        )
        self.service = ChatMessageCreditService()

    def test_get_status_creates_default_db_config_with_ten_daily_credits(self):
        status = self.service.get_status(self.user)

        self.assertEqual(status.limit, 10)
        self.assertEqual(status.used, 0)
        self.assertEqual(status.remaining, 10)
        self.assertEqual(ChatRateLimitConfig.objects.count(), 1)

    def test_consume_credit_increments_used_credits_for_today(self):
        status = self.service.consume_credit(self.user)

        self.assertEqual(status.used, 1)
        self.assertEqual(status.remaining, 9)
        self.assertEqual(
            DailyMessageCreditUsage.objects.get(
                user=self.user, usage_date=timezone.localdate()
            ).used_credits,
            1,
        )

    def test_consume_credit_raises_when_daily_limit_is_reached(self):
        ChatRateLimitConfig.objects.create(singleton_key="default", daily_message_credit_limit=2)

        self.service.consume_credit(self.user)
        self.service.consume_credit(self.user)

        with self.assertRaises(ChatMessageCreditLimitExceededError) as error:
            self.service.consume_credit(self.user)

        self.assertEqual(error.exception.status.limit, 2)
        self.assertEqual(error.exception.status.used, 2)
        self.assertEqual(error.exception.status.remaining, 0)

    def test_get_status_ignores_previous_day_usage(self):
        DailyMessageCreditUsage.objects.create(
            user=self.user,
            usage_date=timezone.localdate() - timedelta(days=1),
            used_credits=7,
        )

        status = self.service.get_status(self.user)

        self.assertEqual(status.used, 0)
        self.assertEqual(status.remaining, 10)
