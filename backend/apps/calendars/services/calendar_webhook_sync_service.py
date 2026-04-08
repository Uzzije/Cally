from __future__ import annotations

import logging
from dataclasses import dataclass

from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.services.calendar_sync_trigger_service import CalendarSyncTriggerService

logger = logging.getLogger(__name__)


class CalendarWebhookAuthenticationError(Exception):
    pass


@dataclass(frozen=True)
class CalendarWebhookSyncResult:
    accepted: bool
    sync_requested: bool
    calendar_id: int | None


class CalendarWebhookSyncService:
    def __init__(self, trigger_service: CalendarSyncTriggerService | None = None) -> None:
        """Authenticate and handle Google Calendar webhook notifications, triggering resyncs when needed."""
        self.trigger_service = trigger_service or CalendarSyncTriggerService()

    def handle_notification(self, *, headers) -> CalendarWebhookSyncResult:
        """Validate webhook headers and request a background sync for relevant resource states."""
        channel_id = self._get_header(headers, "X-Goog-Channel-ID")
        channel_token = self._get_header(headers, "X-Goog-Channel-Token")
        resource_id = self._get_header(headers, "X-Goog-Resource-ID")
        resource_state = self._get_header(headers, "X-Goog-Resource-State")
        message_number = self._get_header(headers, "X-Goog-Message-Number", required=False)

        calendar = (
            Calendar.objects.select_related("user")
            .filter(
                webhook_channel_id=channel_id,
                webhook_channel_token=channel_token,
                webhook_resource_id=resource_id,
            )
            .first()
        )
        if calendar is None:
            raise CalendarWebhookAuthenticationError(
                "Invalid Google calendar webhook notification."
            )

        if calendar.webhook_expires_at and calendar.webhook_expires_at <= timezone.now():
            raise CalendarWebhookAuthenticationError(
                "Expired Google calendar webhook notification."
            )

        logger.info(
            "calendar.webhook.received",
            extra={
                "calendar_id": calendar.id,
                "user_id": calendar.user_id,
                "resource_state": resource_state,
                "message_number": message_number,
            },
        )

        if resource_state == "sync":
            return CalendarWebhookSyncResult(
                accepted=True,
                sync_requested=False,
                calendar_id=calendar.id,
            )

        self.trigger_service.request_primary_calendar_sync(calendar.user)
        logger.info(
            "calendar.webhook.sync_requested",
            extra={
                "calendar_id": calendar.id,
                "user_id": calendar.user_id,
                "resource_state": resource_state,
            },
        )
        return CalendarWebhookSyncResult(
            accepted=True,
            sync_requested=True,
            calendar_id=calendar.id,
        )

    def _get_header(self, headers, name: str, *, required: bool = True) -> str:
        value = headers.get(name) or headers.get(name.lower())
        if value:
            return str(value)
        if required:
            raise CalendarWebhookAuthenticationError(
                "Invalid Google calendar webhook notification."
            )
        return ""
