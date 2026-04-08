from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.accounts.services.google_oauth_credential_service import (
    GoogleOAuthCredentialError,
    GoogleOAuthCredentialService,
)
from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event
from apps.calendars.services.google_calendar_client import GoogleCalendarClient
from apps.core.types import AuthenticatedUser

logger = logging.getLogger(__name__)


class CalendarSyncError(Exception):
    pass


class CalendarSyncPrerequisiteError(CalendarSyncError):
    code = "google_reauth_required"


@dataclass(frozen=True)
class CalendarSyncResult:
    calendar_id: int
    event_count: int
    sync_token: str
    last_synced_at: str


class CalendarSyncService:
    def __init__(
        self,
        client: Any | None = None,
        credential_service: GoogleOAuthCredentialService | None = None,
    ) -> None:
        """Sync a user's primary Google Calendar into local Calendar/Event models."""
        self.client = client or GoogleCalendarClient()
        self.credential_service = credential_service or GoogleOAuthCredentialService()

    def ensure_primary_calendar_sync_available(self, user: AuthenticatedUser) -> None:
        """Raise a prerequisite error if the user needs to re-auth Google before syncing."""
        try:
            self.credential_service.get_decrypted_credential(user)
        except GoogleOAuthCredentialError as exc:
            raise CalendarSyncPrerequisiteError(str(exc)) from exc

    def sync_primary_calendar(self, user: AuthenticatedUser) -> CalendarSyncResult:
        """Fetch primary calendar + events from Google and upsert them locally."""
        self.ensure_primary_calendar_sync_available(user)

        try:
            calendar_descriptor = self.client.get_primary_calendar(user)
            existing_calendar = Calendar.objects.filter(
                user=user,
                google_calendar_id=calendar_descriptor.google_calendar_id,
            ).first()
            sync_token = (
                existing_calendar.sync_token
                if existing_calendar and existing_calendar.sync_token
                else None
            )
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
        is_full_sync = sync_token is None

        cancelled_ids = [ep.google_event_id for ep in event_payloads if ep.status == "cancelled"]
        active_payloads = [ep for ep in event_payloads if ep.status != "cancelled"]

        with transaction.atomic():
            calendar, _ = Calendar.objects.update_or_create(
                user=user,
                google_calendar_id=calendar_descriptor.google_calendar_id,
                defaults={
                    "name": calendar_descriptor.name,
                    "is_primary": calendar_descriptor.is_primary,
                    "color": calendar_descriptor.color,
                    "timezone": calendar_descriptor.timezone,
                    "sync_token": next_sync_token,
                    "last_synced_at": synced_at,
                },
            )

            if cancelled_ids:
                Event.objects.filter(
                    calendar=calendar,
                    google_event_id__in=cancelled_ids,
                ).delete()

            for event_payload in active_payloads:
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

            if is_full_sync:
                synced_google_ids = {ep.google_event_id for ep in active_payloads}
                stale_count, _ = (
                    Event.objects.filter(calendar=calendar)
                    .exclude(google_event_id__in=synced_google_ids)
                    .delete()
                )
                if stale_count:
                    logger.info(
                        "Removed stale events during full sync",
                        extra={
                            "user_id": user.id,
                            "calendar_id": calendar.id,
                            "stale_count": stale_count,
                        },
                    )

        return CalendarSyncResult(
            calendar_id=calendar.id,
            event_count=len(active_payloads),
            sync_token=next_sync_token,
            last_synced_at=synced_at.isoformat(),
        )
