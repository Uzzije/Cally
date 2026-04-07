from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.calendars.models.calendar import Calendar
from apps.core.types import AuthenticatedUser
from apps.calendars.models.event import Event
from apps.calendars.services.google_calendar_client import (
    GoogleCalendarClient,
    GoogleCalendarClientError,
)

logger = logging.getLogger(__name__)


class CalendarEventMutationError(Exception):
    pass


@dataclass(frozen=True)
class CalendarEventMutationRequest:
    title: str
    start_time: str
    end_time: str
    timezone: str
    attendee_emails: list[str] = field(default_factory=list)
    description: str = ""
    location: str = ""


@dataclass(frozen=True)
class CalendarEventMutationResult:
    calendar_id: int
    event_id: int
    google_event_id: str


class CalendarEventMutationService:
    def __init__(self, client: GoogleCalendarClient | None = None) -> None:
        self.client = client or GoogleCalendarClient()

    def create_primary_calendar_event(
        self, user: AuthenticatedUser, *, request: CalendarEventMutationRequest
    ) -> CalendarEventMutationResult:
        start_time = parse_datetime(request.start_time)
        end_time = parse_datetime(request.end_time)
        if start_time is None or end_time is None:
            raise CalendarEventMutationError("The proposed time range is invalid.")

        try:
            calendar_descriptor = self.client.get_primary_calendar(user)
            created_event = self.client.create_event(
                user,
                calendar_id=calendar_descriptor.google_calendar_id,
                title=request.title,
                start_time=start_time,
                end_time=end_time,
                timezone_name=request.timezone,
                attendee_emails=request.attendee_emails,
                description=request.description,
                location=request.location,
            )
        except GoogleCalendarClientError as exc:
            raise CalendarEventMutationError("Unable to create the calendar event.") from exc

        reconciled_at = timezone.now()

        with transaction.atomic():
            calendar, _ = Calendar.objects.update_or_create(
                user=user,
                google_calendar_id=calendar_descriptor.google_calendar_id,
                defaults={
                    "name": calendar_descriptor.name,
                    "is_primary": calendar_descriptor.is_primary,
                    "color": calendar_descriptor.color,
                    "timezone": calendar_descriptor.timezone or request.timezone,
                    "last_synced_at": reconciled_at,
                },
            )
            event, _ = Event.objects.update_or_create(
                calendar=calendar,
                google_event_id=created_event.google_event_id,
                defaults={
                    "title": created_event.title,
                    "description": created_event.description,
                    "start_time": created_event.start_time,
                    "end_time": created_event.end_time,
                    "timezone": created_event.timezone,
                    "location": created_event.location,
                    "status": created_event.status,
                    "attendees": created_event.attendees,
                    "organizer_email": created_event.organizer_email,
                    "is_all_day": created_event.is_all_day,
                },
            )

        logger.info(
            "calendar.event.reconciled user_id=%s calendar_id=%s event_id=%s google_event_id=%s",
            user.id,
            calendar.id,
            event.id,
            event.google_event_id,
        )
        return CalendarEventMutationResult(
            calendar_id=calendar.id,
            event_id=event.id,
            google_event_id=event.google_event_id,
        )
