from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.chat.services.chat_planning_constraints_service import ChatPlanningConstraintsService
from apps.preferences.models.temporary_blocked_time import TemporaryBlockedTime
from apps.preferences.models.user_preferences import ExecutionMode, UserPreferences

User = get_user_model()


class ChatPlanningConstraintsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="planning-constraints@example.com",
            password="test-pass-123",
        )

    def test_get_constraints_returns_safe_defaults_when_preferences_are_missing(self):
        constraints = ChatPlanningConstraintsService().get_constraints(self.user)

        self.assertEqual(constraints.execution_mode, ExecutionMode.DRAFT_ONLY)
        self.assertIsNone(constraints.display_timezone)
        self.assertEqual(constraints.blocked_times, [])
        self.assertEqual(constraints.temp_blocked_times, [])

    def test_get_constraints_returns_saved_user_preferences(self):
        UserPreferences.objects.create(
            user=self.user,
            execution_mode=ExecutionMode.CONFIRM,
            display_timezone="America/Los_Angeles",
            blocked_times=[
                {
                    "id": "focus-block",
                    "label": "Focus time",
                    "days": ["mon", "tue"],
                    "start": "09:00",
                    "end": "10:00",
                }
            ],
        )

        constraints = ChatPlanningConstraintsService().get_constraints(self.user)

        self.assertEqual(constraints.execution_mode, ExecutionMode.CONFIRM)
        self.assertEqual(constraints.display_timezone, "America/Los_Angeles")
        self.assertEqual(constraints.blocked_times[0]["id"], "focus-block")

    def test_get_constraints_includes_active_temporary_blocked_times(self):
        TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Short-term hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        constraints = ChatPlanningConstraintsService().get_constraints(self.user)

        self.assertEqual(len(constraints.temp_blocked_times), 1)
        self.assertEqual(constraints.temp_blocked_times[0]["label"], "Short-term hold")
