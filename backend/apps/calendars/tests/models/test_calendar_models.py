from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event

User = get_user_model()


class CalendarModelTests(TestCase):
    def test_calendar_unique_constraint_is_enforced_per_user_and_google_calendar_id(self):
        user = User.objects.create_user(
            username="ignored",
            email="calendar@example.com",
            password="test-pass-123",
        )
        Calendar.objects.create(
            user=user,
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
        )

        with self.assertRaises(IntegrityError):
            Calendar.objects.create(
                user=user,
                google_calendar_id="primary",
                name="Duplicate Primary",
                is_primary=True,
            )

    def test_event_unique_constraint_is_enforced_per_calendar_and_google_event_id(self):
        user = User.objects.create_user(
            username="ignored",
            email="event@example.com",
            password="test-pass-123",
        )
        calendar = Calendar.objects.create(
            user=user,
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
        )
        Event.objects.create(
            calendar=calendar,
            google_event_id="event-1",
            title="Design Review",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
        )

        with self.assertRaises(IntegrityError):
            Event.objects.create(
                calendar=calendar,
                google_event_id="event-1",
                title="Duplicate",
                start_time=timezone.now(),
                end_time=timezone.now() + timedelta(hours=1),
            )

    def test_event_range_query_fields_can_be_persisted_for_weekly_view(self):
        user = User.objects.create_user(
            username="ignored",
            email="range@example.com",
            password="test-pass-123",
        )
        calendar = Calendar.objects.create(
            user=user,
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
        )
        event = Event.objects.create(
            calendar=calendar,
            google_event_id="event-42",
            title="Weekly Planning",
            description="Roadmap review",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            timezone="America/New_York",
            location="Zoom",
            status="confirmed",
            attendees=[{"email": "teammate@example.com"}],
            organizer_email="lead@example.com",
            is_all_day=False,
        )

        self.assertEqual(event.timezone, "America/New_York")
        self.assertEqual(event.location, "Zoom")
        self.assertEqual(event.attendees, [{"email": "teammate@example.com"}])
