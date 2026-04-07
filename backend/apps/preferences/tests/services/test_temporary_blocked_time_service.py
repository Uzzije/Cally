from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.preferences.models.temporary_blocked_time import (
    TemporaryBlockedTime,
    TemporaryBlockedTimeSource,
)
from apps.preferences.services.temporary_blocked_time_service import (
    TemporaryBlockedTimeCreateRequest,
    TemporaryBlockedTimeService,
    TemporaryBlockedTimeValidationError,
)

User = get_user_model()


class TemporaryBlockedTimeServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="temporary-blocked-time@example.com",
            password="test-pass-123",
        )
        self.service = TemporaryBlockedTimeService()

    def test_create_many_for_user_persists_entries_with_expiry(self):
        entries = self.service.create_many_for_user(
            self.user,
            requests=[
                TemporaryBlockedTimeCreateRequest(
                    label="Hold for 30-minute meeting",
                    date="2026-04-08",
                    start="14:00",
                    end="14:30",
                    timezone="America/New_York",
                )
            ],
        )

        self.assertEqual(len(entries), 1)
        blocked_time = entries[0]
        self.assertEqual(blocked_time.source, TemporaryBlockedTimeSource.EMAIL_DRAFT)
        self.assertEqual(blocked_time.timezone, "America/New_York")
        self.assertGreater(blocked_time.expires_at, blocked_time.created_at)
        self.assertEqual(
            self.service.list_active_for_user(self.user)[0].public_id, blocked_time.public_id
        )

    def test_create_many_for_user_rejects_invalid_time_ranges(self):
        with self.assertRaises(TemporaryBlockedTimeValidationError) as error:
            self.service.create_many_for_user(
                self.user,
                requests=[
                    TemporaryBlockedTimeCreateRequest(
                        label="Broken hold",
                        date="2026-04-08",
                        start="15:00",
                        end="14:30",
                        timezone="America/New_York",
                    )
                ],
            )

        self.assertEqual(
            error.exception.errors["entries"],
            ["Entry 1 start time must be earlier than end time."],
        )

    def test_expire_by_public_ids_deletes_only_due_entries(self):
        expired_entry = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Expired hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        active_entry = TemporaryBlockedTime.objects.create(
            user=self.user,
            label="Active hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=59),
        )

        deleted_count = self.service.expire_by_public_ids(
            public_ids=[expired_entry.public_id, active_entry.public_id]
        )

        self.assertEqual(deleted_count, 1)
        self.assertFalse(
            TemporaryBlockedTime.objects.filter(public_id=expired_entry.public_id).exists()
        )
        self.assertTrue(
            TemporaryBlockedTime.objects.filter(public_id=active_entry.public_id).exists()
        )
