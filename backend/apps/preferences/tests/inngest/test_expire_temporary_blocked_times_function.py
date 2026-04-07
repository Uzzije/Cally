from datetime import timedelta
from typing import Any, cast

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.preferences.inngest.functions.expire_temporary_blocked_times_function import (
    expire_temporary_blocked_times_function,
)
from apps.preferences.models.temporary_blocked_time import TemporaryBlockedTime

User = get_user_model()


class _FakeEvent:
    def __init__(self, public_ids):
        self.data = {"public_ids": public_ids}


class _FakeContext:
    def __init__(self, public_ids):
        self.event = _FakeEvent(public_ids)


class _FakeStep:
    def __init__(self):
        self.calls = []

    def sleep(self, step_id, duration):
        self.calls.append((step_id, duration))


class ExpireTemporaryBlockedTimesFunctionTests(TestCase):
    def test_function_waits_then_expires_due_entries(self):
        user = User.objects.create_user(
            username="ignored",
            email="temp-blocked-time-fn@example.com",
            password="test-pass-123",
        )
        expired_entry = TemporaryBlockedTime.objects.create(
            user=user,
            label="Expired hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        active_entry = TemporaryBlockedTime.objects.create(
            user=user,
            label="Active hold",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(minutes=30),
            timezone="America/New_York",
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        step = _FakeStep()
        handler = cast(Any, expire_temporary_blocked_times_function)._handler
        result: dict[str, Any] = handler(
            _FakeContext([expired_entry.public_id, active_entry.public_id]),
            step,
        )

        self.assertEqual(step.calls[0][0], "wait-one-hour")
        self.assertEqual(result["expired_count"], 1)
        self.assertFalse(
            TemporaryBlockedTime.objects.filter(public_id=expired_entry.public_id).exists()
        )
        self.assertTrue(
            TemporaryBlockedTime.objects.filter(public_id=active_entry.public_id).exists()
        )
