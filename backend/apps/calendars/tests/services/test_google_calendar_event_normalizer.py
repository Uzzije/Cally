from django.test import SimpleTestCase
from django.utils.timezone import is_aware

from apps.calendars.services.google_calendar_event_normalizer import normalize_google_event


class GoogleCalendarEventNormalizerTests(SimpleTestCase):
    def test_normalizes_timed_event(self):
        payload = {
            "id": "evt-1",
            "summary": "Design Review",
            "description": "Weekly sync",
            "start": {
                "dateTime": "2026-04-06T14:00:00Z",
                "timeZone": "America/New_York",
            },
            "end": {
                "dateTime": "2026-04-06T15:00:00Z",
                "timeZone": "America/New_York",
            },
            "location": "Zoom",
            "status": "confirmed",
            "attendees": [{"email": "teammate@example.com"}],
            "organizer": {"email": "owner@example.com"},
        }

        normalized = normalize_google_event(payload)

        self.assertEqual(normalized.google_event_id, "evt-1")
        self.assertEqual(normalized.title, "Design Review")
        self.assertFalse(normalized.is_all_day)
        self.assertTrue(is_aware(normalized.start_time))
        self.assertEqual(normalized.location, "Zoom")

    def test_normalizes_all_day_event(self):
        payload = {
            "id": "evt-2",
            "summary": "Holiday",
            "start": {"date": "2026-04-08", "timeZone": "America/New_York"},
            "end": {"date": "2026-04-09", "timeZone": "America/New_York"},
        }

        normalized = normalize_google_event(payload)

        self.assertTrue(normalized.is_all_day)
        self.assertEqual(normalized.timezone, "America/New_York")
        self.assertEqual(normalized.title, "Holiday")
        self.assertTrue(is_aware(normalized.start_time))
        self.assertEqual(normalized.start_time.tzinfo.key, "America/New_York")

    def test_normalizes_datetime_without_offset_using_google_timezone(self):
        payload = {
            "id": "evt-4",
            "summary": "Focused Work",
            "start": {
                "dateTime": "2026-04-06T09:00:00",
                "timeZone": "America/Los_Angeles",
            },
            "end": {
                "dateTime": "2026-04-06T10:30:00",
                "timeZone": "America/Los_Angeles",
            },
        }

        normalized = normalize_google_event(payload)

        self.assertTrue(is_aware(normalized.start_time))
        self.assertTrue(is_aware(normalized.end_time))
        self.assertEqual(normalized.start_time.tzinfo.key, "America/Los_Angeles")
        self.assertEqual(normalized.end_time.tzinfo.key, "America/Los_Angeles")

    def test_handles_missing_optional_fields(self):
        payload = {
            "id": "evt-3",
            "start": {"dateTime": "2026-04-06T14:00:00Z"},
            "end": {"dateTime": "2026-04-06T15:00:00Z"},
        }

        normalized = normalize_google_event(payload)

        self.assertEqual(normalized.title, "Untitled event")
        self.assertEqual(normalized.description, "")
        self.assertEqual(normalized.location, "")
        self.assertEqual(normalized.attendees, [])
