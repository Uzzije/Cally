from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

from django.test import SimpleTestCase

from apps.calendars.services.calendar_attendee_availability_service import (
    CalendarAttendeeAvailabilityService,
)
from apps.calendars.services.google_calendar_client import GoogleCalendarClientError


class CalendarAttendeeAvailabilityServiceTests(SimpleTestCase):
    def test_returns_empty_non_degraded_result_when_no_attendee_emails(self):
        google_client = Mock()
        service = CalendarAttendeeAvailabilityService(google_calendar_client=google_client)

        result = service.lookup_attendee_busy_ranges(
            user=Mock(id=7),
            attendee_emails=["Joe", ""],
            start=datetime.fromisoformat("2026-04-07T09:00:00+00:00"),
            end=datetime.fromisoformat("2026-04-07T17:00:00+00:00"),
        )

        self.assertEqual(result.busy_ranges_by_attendee, {})
        self.assertFalse(result.degraded)
        google_client.get_free_busy.assert_not_called()

    def test_returns_degraded_result_when_google_client_fails(self):
        google_client = Mock()
        google_client.get_free_busy.side_effect = GoogleCalendarClientError("boom")
        service = CalendarAttendeeAvailabilityService(google_calendar_client=google_client)

        result = service.lookup_attendee_busy_ranges(
            user=Mock(id=7),
            attendee_emails=["joe@example.com"],
            start=datetime.fromisoformat("2026-04-07T09:00:00+00:00"),
            end=datetime.fromisoformat("2026-04-07T17:00:00+00:00"),
        )

        self.assertEqual(result.busy_ranges_by_attendee, {})
        self.assertTrue(result.degraded)

    def test_returns_attendee_busy_ranges_when_lookup_succeeds(self):
        google_client = Mock()
        google_client.get_free_busy.return_value = {
            "joe@example.com": [
                (
                    datetime.fromisoformat("2026-04-07T10:00:00+00:00"),
                    datetime.fromisoformat("2026-04-07T11:00:00+00:00"),
                )
            ]
        }
        service = CalendarAttendeeAvailabilityService(google_calendar_client=google_client)

        result = service.lookup_attendee_busy_ranges(
            user=Mock(id=7),
            attendee_emails=["joe@example.com"],
            start=datetime.fromisoformat("2026-04-07T09:00:00+00:00"),
            end=datetime.fromisoformat("2026-04-07T17:00:00+00:00"),
        )

        self.assertFalse(result.degraded)
        self.assertEqual(len(result.busy_ranges_by_attendee["joe@example.com"]), 1)
