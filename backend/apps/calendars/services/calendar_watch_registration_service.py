from __future__ import annotations

import logging
import secrets
from datetime import timedelta
import uuid

from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.core.types import AuthenticatedUser
from apps.calendars.services.calendar_webhook_address_resolver_service import (
    CalendarWebhookAddressResolverService,
)
from apps.calendars.services.google_calendar_client import GoogleCalendarClient

logger = logging.getLogger(__name__)


class CalendarWatchRegistrationService:
    def __init__(
        self,
        client: GoogleCalendarClient | None = None,
        *,
        renew_before: timedelta = timedelta(hours=24),
        webhook_address_resolver: CalendarWebhookAddressResolverService | None = None,
    ) -> None:
        self.client = client or GoogleCalendarClient()
        self.renew_before = renew_before
        self.webhook_address_resolver = (
            webhook_address_resolver or CalendarWebhookAddressResolverService()
        )

    def ensure_primary_calendar_watch(self, user: AuthenticatedUser, calendar: Calendar) -> bool:
        webhook_address = self.webhook_address_resolver.resolve()
        if not webhook_address:
            logger.info(
                "calendar.watch.skipped",
                extra={
                    "user_id": user.id,
                    "calendar_id": calendar.id,
                    "reason": "webhook_address_missing",
                },
            )
            return False

        if self._watch_is_current(calendar):
            return False

        previous_channel_id = calendar.webhook_channel_id
        previous_resource_id = calendar.webhook_resource_id
        channel_id = str(uuid.uuid4())
        channel_token = secrets.token_urlsafe(24)
        try:
            subscription = self.client.watch_calendar(
                user,
                calendar_id=calendar.google_calendar_id,
                webhook_address=webhook_address,
                channel_id=channel_id,
                channel_token=channel_token,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "calendar.watch.registration_failed",
                extra={
                    "user_id": user.id,
                    "calendar_id": calendar.id,
                    "reason": str(exc),
                },
            )
            return False
        calendar.webhook_channel_id = subscription.channel_id
        calendar.webhook_channel_token = channel_token
        calendar.webhook_resource_id = subscription.resource_id
        calendar.webhook_expires_at = subscription.expires_at
        calendar.save(
            update_fields=[
                "webhook_channel_id",
                "webhook_channel_token",
                "webhook_resource_id",
                "webhook_expires_at",
                "updated_at",
            ]
        )
        logger.info(
            "calendar.watch.registered",
            extra={
                "user_id": user.id,
                "calendar_id": calendar.id,
                "channel_id": subscription.channel_id,
                "resource_id": subscription.resource_id,
            },
        )
        if previous_channel_id and previous_resource_id:
            try:
                self.client.stop_channel(
                    user,
                    channel_id=previous_channel_id,
                    resource_id=previous_resource_id,
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "calendar.watch.stop_failed",
                    extra={
                        "user_id": user.id,
                        "calendar_id": calendar.id,
                        "channel_id": previous_channel_id,
                        "resource_id": previous_resource_id,
                    },
                )
        return True

    def _watch_is_current(self, calendar: Calendar) -> bool:
        if not (
            calendar.webhook_channel_id
            and calendar.webhook_channel_token
            and calendar.webhook_resource_id
            and calendar.webhook_expires_at
        ):
            return False

        return calendar.webhook_expires_at > timezone.now() + self.renew_before
