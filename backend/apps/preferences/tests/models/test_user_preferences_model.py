from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.preferences.models.user_preferences import ExecutionMode, UserPreferences

User = get_user_model()


class UserPreferencesModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="preferences-model@example.com",
            password="test-pass-123",
        )

    def test_defaults_to_safe_execution_mode_and_empty_blocked_times(self):
        preferences = UserPreferences.objects.create(user=self.user)

        self.assertEqual(preferences.execution_mode, ExecutionMode.DRAFT_ONLY)
        self.assertEqual(preferences.display_timezone, "")
        self.assertEqual(preferences.blocked_times, [])

    def test_enforces_one_preferences_record_per_user(self):
        UserPreferences.objects.create(user=self.user)

        with self.assertRaises(IntegrityError):
            UserPreferences.objects.create(user=self.user)

    def test_exposes_rate_limit_defaults(self):
        preferences = UserPreferences.objects.create(user=self.user)

        self.assertEqual(preferences.email_send_limit_per_hour, 20)
        self.assertEqual(preferences.event_create_limit_per_hour, 10)
