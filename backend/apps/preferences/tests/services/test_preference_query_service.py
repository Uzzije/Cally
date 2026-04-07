from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.preferences.models.temporary_blocked_time import TemporaryBlockedTime
from apps.preferences.models.user_preferences import ExecutionMode, UserPreferences
from apps.preferences.services.preference_query_service import PreferenceQueryService

User = get_user_model()


class PreferenceQueryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="preferences-query@example.com",
            password="test-pass-123",
        )

    def test_get_for_user_creates_safe_defaults_when_missing(self):
        preferences = PreferenceQueryService().get_for_user(self.user)

        self.assertEqual(preferences.execution_mode, ExecutionMode.DRAFT_ONLY)
        self.assertIsNone(PreferenceQueryService().get_display_timezone(self.user))
        self.assertEqual(preferences.blocked_times, [])
        self.assertEqual(UserPreferences.objects.filter(user=self.user).count(), 1)

    def test_get_for_user_normalizes_legacy_auto_mode_to_confirm(self):
        UserPreferences.objects.create(
            user=self.user,
            execution_mode="auto",
            blocked_times=[],
        )

        preferences = PreferenceQueryService().get_for_user(self.user)

        self.assertEqual(preferences.execution_mode, ExecutionMode.CONFIRM)

    def test_get_display_timezone_returns_saved_preference(self):
        UserPreferences.objects.create(
            user=self.user,
            execution_mode=ExecutionMode.CONFIRM,
            display_timezone="America/Los_Angeles",
            blocked_times=[],
        )

        display_timezone = PreferenceQueryService().get_display_timezone(self.user)

        self.assertEqual(display_timezone, "America/Los_Angeles")

    def test_get_active_temporary_blocked_times_returns_only_unexpired_entries(self):
        expired_entry = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Expired hold",
            start_time=timezone.now(),
            end_time=timezone.now(),
            timezone="America/New_York",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        active_entry = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Active hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        results = list(PreferenceQueryService().get_active_temporary_blocked_times(self.user))

        self.assertEqual([entry.public_id for entry in results], [active_entry.public_id])
        self.assertNotIn(expired_entry.public_id, [entry.public_id for entry in results])
