from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event
from apps.preferences.services.preference_query_service import PreferenceQueryService


@dataclass(frozen=True)
class CalendarSyncStatusResult:
    has_calendar: bool
    sync_state: str
    last_synced_at: str | None
    is_stale: bool


class CalendarQueryService:
    stale_after = timedelta(minutes=15)

    def __init__(
        self,
        *,
        preference_query_service: PreferenceQueryService | None = None,
    ) -> None:
        self.preference_query_service = preference_query_service or PreferenceQueryService()

    def get_primary_calendar(self, user) -> Calendar | None:
        return Calendar.objects.filter(user=user, is_primary=True).first()

    def get_default_timezone(self, user) -> str:
        preferred_timezone = self.preference_query_service.get_display_timezone(user)
        if preferred_timezone:
            return preferred_timezone

        calendar = self.get_primary_calendar(user)
        if calendar and calendar.timezone:
            return calendar.timezone

        event = (
            Event.objects.filter(calendar__user=user, calendar__is_primary=True)
            .exclude(timezone="")
            .order_by("-start_time", "-id")
            .first()
        )
        if event and event.timezone:
            return event.timezone

        return getattr(settings, "TIME_ZONE", "UTC")

    def get_events_for_range(self, user, *, start: datetime, end: datetime):
        return (
            Event.objects.select_related("calendar")
            .filter(
                calendar__user=user,
                calendar__is_primary=True,
                start_time__lt=end,
                end_time__gt=start,
            )
            .order_by("start_time", "id")
        )

    def search_events(self, user, *, query: str, limit: int = 5):
        return (
            Event.objects.select_related("calendar")
            .filter(calendar__user=user, calendar__is_primary=True)
            .filter(
                models.Q(title__icontains=query)
                | models.Q(description__icontains=query)
                | models.Q(location__icontains=query)
                | models.Q(organizer_email__icontains=query)
            )
            .order_by("start_time", "id")[:limit]
        )

    def get_sync_status(self, user) -> CalendarSyncStatusResult:
        calendar = self.get_primary_calendar(user)
        if calendar is None:
            return CalendarSyncStatusResult(
                has_calendar=False,
                sync_state="not_started",
                last_synced_at=None,
                is_stale=False,
            )

        if calendar.last_synced_at is None:
            return CalendarSyncStatusResult(
                has_calendar=True,
                sync_state="syncing",
                last_synced_at=None,
                is_stale=False,
            )

        is_stale = calendar.last_synced_at < timezone.now() - self.stale_after
        return CalendarSyncStatusResult(
            has_calendar=True,
            sync_state="stale" if is_stale else "ready",
            last_synced_at=calendar.last_synced_at.isoformat(),
            is_stale=is_stale,
        )
