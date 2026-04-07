from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.calendars.services.calendar_query_service import CalendarQueryService
from apps.preferences.models.user_preferences import UserPreferences

User = get_user_model()


class CalendarQueryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="calendar-query@example.com",
            password="test-pass-123",
        )

    def test_get_default_timezone_prefers_saved_display_timezone(self):
        UserPreferences.objects.create(
            user=self.user,
            display_timezone="America/Los_Angeles",
        )

        default_timezone = CalendarQueryService().get_default_timezone(self.user)

        self.assertEqual(default_timezone, "America/Los_Angeles")

    def test_get_default_timezone_falls_back_to_application_timezone(self):
        default_timezone = CalendarQueryService().get_default_timezone(self.user)

        self.assertEqual(default_timezone, settings.TIME_ZONE)
