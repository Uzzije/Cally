from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event
from apps.calendars.services.calendar_event_mutation_service import (
    CalendarEventMutationRequest,
    CalendarEventMutationService,
)
from apps.calendars.services.google_calendar_payloads import (
    CalendarEventPayload,
    GoogleCalendarDescriptor,
)

User = get_user_model()


class CalendarEventMutationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="calendar-mutation-user",
            email="calendar-mutation@example.com",
            password="test-pass-123",
        )
        self.client = Mock()
        self.client.get_primary_calendar.return_value = GoogleCalendarDescriptor(
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
            color="#C05746",
            timezone="America/New_York",
        )
        self.client.create_event.return_value = CalendarEventPayload(
            google_event_id="google-event-1",
            title="Meeting with Joe",
            description="",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            location="",
            status="confirmed",
            attendees=[{"email": "joe@example.com"}],
            organizer_email="owner@example.com",
            is_all_day=False,
        )
        self.service = CalendarEventMutationService(client=self.client)

    def test_create_primary_calendar_event_reconciles_event_into_local_store(self):
        result = self.service.create_primary_calendar_event(
            self.user,
            request=CalendarEventMutationRequest(
                title="Meeting with Joe",
                start_time="2026-04-07T13:00:00+00:00",
                end_time="2026-04-07T13:30:00+00:00",
                timezone="America/New_York",
                attendee_emails=["joe@example.com"],
            ),
        )

        calendar = Calendar.objects.get(user=self.user, google_calendar_id="primary")
        event = Event.objects.get(calendar=calendar, google_event_id="google-event-1")
        self.assertEqual(result.calendar_id, calendar.id)
        self.assertEqual(result.event_id, event.id)
        self.assertEqual(calendar.timezone, "America/New_York")
        self.assertEqual(event.title, "Meeting with Joe")
        self.assertEqual(event.attendees[0]["email"], "joe@example.com")
