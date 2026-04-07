from datetime import timedelta
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.services.calendar_webhook_sync_service import (
    CalendarWebhookAuthenticationError,
    CalendarWebhookSyncService,
)

User = get_user_model()


class CalendarWebhookSyncServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="webhook@example.com",
            password="test-pass-123",
        )
        self.calendar = Calendar.objects.create(
            user=self.user,
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
            webhook_channel_id="channel-123",
            webhook_resource_id="resource-456",
            webhook_channel_token="secret-token",
            webhook_expires_at=timezone.now() + timedelta(days=7),
        )

    def test_valid_notification_enqueues_calendar_sync(self):
        trigger_service = Mock()

        result = CalendarWebhookSyncService(trigger_service=trigger_service).handle_notification(
            headers={
                "X-Goog-Channel-ID": "channel-123",
                "X-Goog-Channel-Token": "secret-token",
                "X-Goog-Resource-ID": "resource-456",
                "X-Goog-Resource-State": "exists",
                "X-Goog-Message-Number": "10",
            }
        )

        self.assertTrue(result.accepted)
        self.assertTrue(result.sync_requested)
        self.assertEqual(result.calendar_id, self.calendar.id)
        trigger_service.request_primary_calendar_sync.assert_called_once_with(self.user)

    def test_sync_handshake_notification_is_accepted_without_enqueueing_sync(self):
        trigger_service = Mock()

        result = CalendarWebhookSyncService(trigger_service=trigger_service).handle_notification(
            headers={
                "X-Goog-Channel-ID": "channel-123",
                "X-Goog-Channel-Token": "secret-token",
                "X-Goog-Resource-ID": "resource-456",
                "X-Goog-Resource-State": "sync",
                "X-Goog-Message-Number": "1",
            }
        )

        self.assertTrue(result.accepted)
        self.assertFalse(result.sync_requested)
        trigger_service.request_primary_calendar_sync.assert_not_called()

    def test_invalid_notification_headers_are_rejected(self):
        trigger_service = Mock()

        with self.assertRaises(CalendarWebhookAuthenticationError):
            CalendarWebhookSyncService(trigger_service=trigger_service).handle_notification(
                headers={
                    "X-Goog-Channel-ID": "channel-123",
                    "X-Goog-Channel-Token": "wrong-token",
                    "X-Goog-Resource-ID": "resource-456",
                    "X-Goog-Resource-State": "exists",
                }
            )

        trigger_service.request_primary_calendar_sync.assert_not_called()
