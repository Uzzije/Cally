from __future__ import annotations

import logging
from dataclasses import dataclass

from allauth.socialaccount.models import SocialToken
from django.db import transaction
from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event
from apps.calendars.services.google_calendar_client import GoogleCalendarClient


logger = logging.getLogger(__name__)


class CalendarSyncError(Exception):
    pass


@dataclass(frozen=True)
class CalendarSyncResult:
    calendar_id: int
    event_count: int
    sync_token: str
    last_synced_at: str


class CalendarSyncService:
    def __init__(self, client: GoogleCalendarClient | None = None) -> None:
        self.client = client or GoogleCalendarClient()

    def sync_primary_calendar(self, user) -> CalendarSyncResult:
        if not SocialToken.objects.filter(account__user=user, account__provider="google").exists():
            raise CalendarSyncError("Google account token is not available for calendar sync.")

        try:
            calendar_descriptor = self.client.get_primary_calendar(user)
            existing_calendar = Calendar.objects.filter(
                user=user,
                google_calendar_id=calendar_descriptor.google_calendar_id,
            ).first()
            sync_token = existing_calendar.sync_token or None if existing_calendar else None
            event_payloads, next_sync_token = self.client.list_events(
                user,
                calendar_id=calendar_descriptor.google_calendar_id,
                sync_token=sync_token,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Primary calendar sync failed",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                },
            )
            raise CalendarSyncError("Unable to synchronize the primary calendar.") from exc

        synced_at = timezone.now()

        with transaction.atomic():
            calendar, _ = Calendar.objects.update_or_create(
                user=user,
                google_calendar_id=calendar_descriptor.google_calendar_id,
                defaults={
                    "name": calendar_descriptor.name,
                    "is_primary": calendar_descriptor.is_primary,
                    "color": calendar_descriptor.color,
                    "sync_token": next_sync_token,
                    "last_synced_at": synced_at,
                },
            )

            for event_payload in event_payloads:
                Event.objects.update_or_create(
                    calendar=calendar,
                    google_event_id=event_payload.google_event_id,
                    defaults={
                        "title": event_payload.title,
                        "description": event_payload.description,
                        "start_time": event_payload.start_time,
                        "end_time": event_payload.end_time,
                        "timezone": event_payload.timezone,
                        "location": event_payload.location,
                        "status": event_payload.status,
                        "attendees": event_payload.attendees,
                        "organizer_email": event_payload.organizer_email,
                        "is_all_day": event_payload.is_all_day,
                    },
                )

        return CalendarSyncResult(
            calendar_id=calendar.id,
            event_count=len(event_payloads),
            sync_token=next_sync_token,
            last_synced_at=synced_at.isoformat(),
        )
