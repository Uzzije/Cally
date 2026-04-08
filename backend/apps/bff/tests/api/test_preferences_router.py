from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.preferences.models.temporary_blocked_time import TemporaryBlockedTime
from apps.preferences.models.user_preferences import ExecutionMode, UserPreferences

User = get_user_model()


class PreferencesRouterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="preferences-api@example.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="ignored-other",
            email="preferences-api-other@example.com",
            password="test-pass-123",
        )

    def test_get_preferences_requires_authentication(self):
        response = self.client.get("/api/v1/settings/preferences", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 401)

    def test_get_preferences_returns_safe_defaults_for_empty_state(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/settings/preferences", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["execution_mode"], ExecutionMode.DRAFT_ONLY)
        self.assertIsNone(response.json()["display_timezone"])
        self.assertEqual(response.json()["blocked_times"], [])

    def test_put_preferences_updates_only_authenticated_users_record(self):
        self.client.force_login(self.user)
        UserPreferences.objects.create(
            user=self.other_user,
            execution_mode=ExecutionMode.CONFIRM,
            blocked_times=[
                {
                    "id": "other-user-block",
                    "label": "Private",
                    "days": ["tue"],
                    "start": "10:00",
                    "end": "11:00",
                }
            ],
        )

        response = self.client.put(
            "/api/v1/settings/preferences",
            data={
                "execution_mode": ExecutionMode.CONFIRM,
                "display_timezone": "America/New_York",
                "blocked_times": [
                    {
                        "label": "Morning workout",
                        "days": ["mon", "tue"],
                        "start": "07:00",
                        "end": "08:30",
                    }
                ],
            },
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["execution_mode"], ExecutionMode.CONFIRM)
        self.assertEqual(payload["display_timezone"], "America/New_York")
        self.assertEqual(len(payload["blocked_times"]), 1)

        other_preferences = UserPreferences.objects.get(user=self.other_user)
        self.assertEqual(other_preferences.execution_mode, ExecutionMode.CONFIRM)
        self.assertEqual(other_preferences.blocked_times[0]["id"], "other-user-block")

    def test_put_preferences_returns_validation_errors(self):
        self.client.force_login(self.user)

        response = self.client.put(
            "/api/v1/settings/preferences",
            data={
                "execution_mode": ExecutionMode.DRAFT_ONLY,
                "display_timezone": "Mars/Olympus_Mons",
                "blocked_times": [],
            },
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Preferences payload is invalid.")
        self.assertIn("display_timezone", response.json()["errors"])

    def test_post_temp_blocked_times_creates_entries_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/settings/temp-blocked-times",
            data={
                "timezone": "America/New_York",
                "entries": [
                    {
                        "label": "Hold for 30-minute meeting next week",
                        "date": "2026-04-08",
                        "start": "14:00",
                        "end": "14:30",
                        "source": "email_draft",
                    }
                ],
            },
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["source"], "email_draft")
        self.assertEqual(
            TemporaryBlockedTime.objects.filter(user=self.user).count(),
            1,
        )

    def test_post_temp_blocked_times_upserts_existing_entry_for_same_time_range(self):
        self.client.force_login(self.user)
        existing_entry = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Original hold",
            start_time=timezone.make_aware(datetime(2026, 4, 8, 14, 0), ZoneInfo("America/New_York")),
            end_time=timezone.make_aware(datetime(2026, 4, 8, 14, 30), ZoneInfo("America/New_York")),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        response = self.client.post(
            "/api/v1/settings/temp-blocked-times",
            data={
                "timezone": "America/New_York",
                "entries": [
                    {
                        "label": "Updated hold",
                        "date": "2026-04-08",
                        "start": "14:00",
                        "end": "14:30",
                        "source": "email_draft",
                    }
                ],
            },
            content_type="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["id"], existing_entry.public_id)
        self.assertEqual(payload["entries"][0]["label"], "Updated hold")
        self.assertEqual(TemporaryBlockedTime.objects.filter(user=self.user).count(), 1)

    def test_get_temp_blocked_times_returns_only_active_entries(self):
        self.client.force_login(self.user)
        TemporaryBlockedTime.objects.create(
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

        response = self.client.get("/api/v1/settings/temp-blocked-times", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entries"][0]["id"], active_entry.public_id)

    def test_delete_temp_blocked_time_removes_only_authenticated_users_entry(self):
        self.client.force_login(self.user)
        own_entry = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Own hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        other_entry = TemporaryBlockedTime.objects.create(
            user=self.other_user,
            label="Other hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        response = self.client.delete(
            f"/api/v1/settings/temp-blocked-times/{own_entry.public_id}",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            TemporaryBlockedTime.objects.filter(public_id=own_entry.public_id).exists()
        )
        self.assertTrue(
            TemporaryBlockedTime.objects.filter(public_id=other_entry.public_id).exists()
        )
