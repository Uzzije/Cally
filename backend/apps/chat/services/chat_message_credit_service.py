from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.chat.models.chat_rate_limit_config import ChatRateLimitConfig
from apps.core.types import AuthenticatedUser
from apps.chat.models.daily_message_credit_usage import DailyMessageCreditUsage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatMessageCreditStatus:
    limit: int
    used: int
    remaining: int
    usage_date: str


class ChatMessageCreditLimitExceededError(Exception):
    def __init__(self, status: ChatMessageCreditStatus) -> None:
        super().__init__(f"You have used all {status.limit} AI message credits for today.")
        self.status = status


class ChatMessageCreditService:
    config_singleton_key = "default"

    def get_config(self) -> ChatRateLimitConfig:
        """Return the rate limit configuration singleton."""
        config, _ = ChatRateLimitConfig.objects.get_or_create(
            singleton_key=self.config_singleton_key
        )
        return config

    def get_status(self, user: AuthenticatedUser) -> ChatMessageCreditStatus:
        """Return today's credit usage and remaining credits for the user."""
        config = self.get_config()
        usage_date = timezone.localdate()
        used = (
            DailyMessageCreditUsage.objects.filter(user=user, usage_date=usage_date)
            .values_list("used_credits", flat=True)
            .first()
            or 0
        )
        remaining = max(config.daily_message_credit_limit - used, 0)
        return ChatMessageCreditStatus(
            limit=config.daily_message_credit_limit,
            used=used,
            remaining=remaining,
            usage_date=usage_date.isoformat(),
        )

    def consume_credit(self, user: AuthenticatedUser) -> ChatMessageCreditStatus:
        """Atomically consume one credit for today, raising when the daily limit is exceeded."""
        usage_date = timezone.localdate()
        config = self.get_config()

        with transaction.atomic():
            usage, _ = DailyMessageCreditUsage.objects.select_for_update().get_or_create(
                user=user,
                usage_date=usage_date,
                defaults={"used_credits": 0},
            )

            if usage.used_credits >= config.daily_message_credit_limit:
                status = ChatMessageCreditStatus(
                    limit=config.daily_message_credit_limit,
                    used=usage.used_credits,
                    remaining=0,
                    usage_date=usage_date.isoformat(),
                )
                logger.warning(
                    "chat.message_credit_limit_exceeded user_id=%s usage_date=%s used=%s limit=%s",
                    user.id,
                    usage_date.isoformat(),
                    usage.used_credits,
                    config.daily_message_credit_limit,
                )
                raise ChatMessageCreditLimitExceededError(status)

            usage.used_credits += 1
            usage.save(update_fields=["used_credits", "updated_at"])

        remaining = max(config.daily_message_credit_limit - usage.used_credits, 0)
        logger.info(
            "chat.message_credit_consumed user_id=%s usage_date=%s used=%s remaining=%s limit=%s",
            user.id,
            usage_date.isoformat(),
            usage.used_credits,
            remaining,
            config.daily_message_credit_limit,
        )
        return ChatMessageCreditStatus(
            limit=config.daily_message_credit_limit,
            used=usage.used_credits,
            remaining=remaining,
            usage_date=usage_date.isoformat(),
        )
