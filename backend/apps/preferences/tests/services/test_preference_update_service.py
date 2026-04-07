from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.preferences.models.user_preferences import ExecutionMode
from apps.preferences.services.preference_update_service import PreferenceUpdateService
from apps.preferences.services.preferences_validation_error import PreferencesValidationError

User = get_user_model()


class PreferenceUpdateServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="preferences-update@example.com",
            password="test-pass-123",
        )

    def test_update_for_user_persists_valid_preferences(self):
        preferences = PreferenceUpdateService().update_for_user(
            self.user,
            execution_mode=ExecutionMode.CONFIRM,
            display_timezone="America/New_York",
            blocked_times=[
                {
                    "label": "Morning workout",
                    "days": ["fri", "mon", "wed", "mon"],
                    "start": "07:00",
                    "end": "09:00",
                }
            ],
        )

        self.assertEqual(preferences.execution_mode, ExecutionMode.CONFIRM)
        self.assertEqual(preferences.display_timezone, "America/New_York")
        self.assertEqual(preferences.blocked_times[0]["days"], ["mon", "wed", "fri"])
        self.assertTrue(preferences.blocked_times[0]["id"])

    def test_update_for_user_rejects_invalid_execution_mode(self):
        with self.assertRaises(PreferencesValidationError) as error:
            PreferenceUpdateService().update_for_user(
                self.user,
                execution_mode="ship_it",
                display_timezone=None,
                blocked_times=[],
            )

        self.assertEqual(
            error.exception.errors["execution_mode"],
            ["Select a valid execution mode."],
        )

    def test_update_for_user_rejects_invalid_time_range(self):
        with self.assertRaises(PreferencesValidationError) as error:
            PreferenceUpdateService().update_for_user(
                self.user,
                execution_mode=ExecutionMode.DRAFT_ONLY,
                display_timezone=None,
                blocked_times=[
                    {
                        "label": "Bad window",
                        "days": ["mon"],
                        "start": "09:00",
                        "end": "08:00",
                    }
                ],
            )

        self.assertEqual(
            error.exception.errors["blocked_times"],
            ["Entry 1 start time must be earlier than end time."],
        )

    def test_update_for_user_rejects_overlapping_entries(self):
        with self.assertRaises(PreferencesValidationError) as error:
            PreferenceUpdateService().update_for_user(
                self.user,
                execution_mode=ExecutionMode.DRAFT_ONLY,
                display_timezone=None,
                blocked_times=[
                    {
                        "label": "Workout",
                        "days": ["mon"],
                        "start": "07:00",
                        "end": "08:00",
                    },
                    {
                        "label": "School run",
                        "days": ["mon"],
                        "start": "07:30",
                        "end": "08:30",
                    },
                ],
            )

        self.assertEqual(
            error.exception.errors["blocked_times"],
            ["Blocked times cannot overlap on Mon."],
        )

    def test_update_for_user_rejects_invalid_display_timezone(self):
        with self.assertRaises(PreferencesValidationError) as error:
            PreferenceUpdateService().update_for_user(
                self.user,
                execution_mode=ExecutionMode.DRAFT_ONLY,
                display_timezone="Mars/Olympus_Mons",
                blocked_times=[],
            )

        self.assertEqual(
            error.exception.errors["display_timezone"],
            ["Select a valid IANA timezone."],
        )
