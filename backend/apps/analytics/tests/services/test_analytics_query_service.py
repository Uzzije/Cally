from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.analytics.services.analytics_query_service import (
    AnalyticsQueryService,
    AnalyticsQueryServiceError,
)
from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event

User = get_user_model()


class AnalyticsQueryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="analytics@example.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="ignored-2",
            email="analytics-other@example.com",
            password="test-pass-123",
        )
        self.calendar = Calendar.objects.create(
            user=self.user,
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
            timezone="America/New_York",
            last_synced_at=timezone.now(),
        )
        self.other_calendar = Calendar.objects.create(
            user=self.other_user,
            google_calendar_id="primary-other",
            name="Primary",
            is_primary=True,
            timezone="America/New_York",
            last_synced_at=timezone.now(),
        )
        now = timezone.now()
        Event.objects.create(
            calendar=self.calendar,
            google_event_id="event-1",
            title="Design review",
            description="Weekly review",
            start_time=now - timedelta(days=1, hours=2),
            end_time=now - timedelta(days=1, hours=1),
            timezone="America/New_York",
            organizer_email="owner@example.com",
        )
        Event.objects.create(
            calendar=self.calendar,
            google_event_id="event-2",
            title="Planning",
            description="Planning session",
            start_time=now - timedelta(days=2, hours=3),
            end_time=now - timedelta(days=2, hours=1),
            timezone="America/New_York",
            organizer_email="owner@example.com",
        )
        Event.objects.create(
            calendar=self.other_calendar,
            google_event_id="event-foreign",
            title="Foreign meeting",
            description="Should not appear",
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1, hours=-1),
            timezone="America/New_York",
            organizer_email="foreign@example.com",
        )
        self.service = AnalyticsQueryService()

    def test_run_returns_meeting_hours_by_weekday_chart(self):
        result = self.service.run(user=self.user, query_type="meeting_hours_by_weekday_this_week")

        self.assertIn("hours of meetings", result.summary_text)
        self.assertEqual(result.chart_block["type"], "chart")
        self.assertEqual(result.chart_block["chart_type"], "bar")
        self.assertEqual(len(result.chart_block["data"]), 7)
        self.assertTrue(result.chart_block["save_enabled"])

    def test_run_returns_busiest_day_last_14_days_chart(self):
        result = self.service.run(user=self.user, query_type="busiest_day_last_14_days")

        self.assertIn("busiest day", result.summary_text.lower())
        self.assertEqual(result.chart_block["title"], "Busiest days in the last 14 days")
        self.assertGreaterEqual(result.chart_block["data"][0]["value"], 0)

    def test_run_rejects_unsupported_query_type(self):
        with self.assertRaises(AnalyticsQueryServiceError):
            self.service.run(user=self.user, query_type="arbitrary_sql")

    def test_run_scopes_results_to_authenticated_user(self):
        result = self.service.run(user=self.user, query_type="busiest_day_last_14_days")

        total_count = sum(point["value"] for point in result.chart_block["data"])
        self.assertEqual(total_count, 2)
