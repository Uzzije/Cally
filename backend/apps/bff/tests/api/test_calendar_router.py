from datetime import timedelta
from unittest.mock import patch
from typing import Any, cast

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event
from apps.calendars.services.calendar_sync_service import CalendarSyncPrerequisiteError

User = get_user_model()


class CalendarRouterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="calendar-api@example.com",
            password="test-pass-123",
        )
        self.other_user = User.objects.create_user(
            username="ignored-other",
            email="other-calendar-api@example.com",
            password="test-pass-123",
        )

    def test_events_requires_authentication(self):
        start = timezone.now().isoformat()
        end = (timezone.now() + timedelta(days=7)).isoformat()

        response = self.client.get(
            f"/api/v1/calendar/events?start={start}&end={end}", HTTP_HOST="localhost"
        )

        self.assertEqual(response.status_code, 401)

    def test_events_returns_only_authenticated_users_primary_calendar_events(self):
        self.client.force_login(self.user)
        calendar = Calendar.objects.create(
            user=self.user,
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
            last_synced_at=timezone.now(),
        )
        Event.objects.create(
            calendar=calendar,
            google_event_id="owned-event",
            title="Owned",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
        )
        other_calendar = Calendar.objects.create(
            user=self.other_user,
            google_calendar_id="other-primary",
            name="Other Primary",
            is_primary=True,
            last_synced_at=timezone.now(),
        )
        Event.objects.create(
            calendar=other_calendar,
            google_event_id="other-event",
            title="Other",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
        )

        start = (timezone.now() - timedelta(hours=1)).isoformat()
        end = (timezone.now() + timedelta(days=7)).isoformat()
        response = self.client.get(
            f"/api/v1/calendar/events?start={start}&end={end}", HTTP_HOST="localhost"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["events"]), 1)
        self.assertEqual(payload["events"][0]["google_event_id"], "owned-event")

    def test_events_applies_requested_range_filter(self):
        self.client.force_login(self.user)
        calendar = Calendar.objects.create(
            user=self.user,
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
            last_synced_at=timezone.now(),
        )
        week_start = timezone.now()
        Event.objects.create(
            calendar=calendar,
            google_event_id="in-range",
            title="In Range",
            start_time=week_start + timedelta(days=1),
            end_time=week_start + timedelta(days=1, hours=1),
        )
        Event.objects.create(
            calendar=calendar,
            google_event_id="out-of-range",
            title="Out Of Range",
            start_time=week_start + timedelta(days=10),
            end_time=week_start + timedelta(days=10, hours=1),
        )

        response = self.client.get(
            f"/api/v1/calendar/events?start={week_start.isoformat()}&end={(week_start + timedelta(days=7)).isoformat()}",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([event["google_event_id"] for event in payload["events"]], ["in-range"])

    def test_sync_status_returns_not_started_payload_without_calendar(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/calendar/sync-status", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "has_calendar": False,
                "sync_state": "not_started",
                "last_synced_at": None,
                "is_stale": False,
            },
        )

    def test_sync_status_marks_calendar_as_stale_when_old(self):
        self.client.force_login(self.user)
        Calendar.objects.create(
            user=self.user,
            google_calendar_id="primary",
            name="Primary",
            is_primary=True,
            last_synced_at=timezone.now() - timedelta(hours=1),
        )

        response = self.client.get("/api/v1/calendar/sync-status", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_stale"])
        self.assertEqual(response.json()["sync_state"], "stale")

    @patch("apps.bff.api.routers.calendar_router.CalendarSyncTriggerService")
    @patch("apps.bff.api.routers.calendar_router.CalendarSyncService")
    def test_sync_endpoint_triggers_primary_calendar_sync(self, sync_service_class, service_class):
        self.client.force_login(self.user)
        sync_service_class.return_value.ensure_primary_calendar_sync_available.return_value = None
        service_class.return_value.request_primary_calendar_sync.return_value = ["event-id-1"]

        response = self.client.post("/api/v1/calendar/sync", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"accepted": True, "event_ids": ["event-id-1"]})
        sync_service_class.return_value.ensure_primary_calendar_sync_available.assert_called_once_with(
            self.user
        )
        service_class.return_value.request_primary_calendar_sync.assert_called_once_with(self.user)

    @patch("apps.bff.api.routers.calendar_router.CalendarSyncTriggerService")
    @patch("apps.bff.api.routers.calendar_router.CalendarSyncService")
    def test_sync_endpoint_returns_reconnect_error_when_google_credential_is_unusable(
        self, sync_service_class, service_class
    ):
        self.client.force_login(self.user)
        sync_service_class.return_value.ensure_primary_calendar_sync_available.side_effect = (
            CalendarSyncPrerequisiteError(
                "Stored Google credential could not be decrypted. Please reconnect Google Calendar."
            )
        )

        response = self.client.post("/api/v1/calendar/sync", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "detail": "Stored Google credential could not be decrypted. Please reconnect Google Calendar.",
                "code": "google_reauth_required",
            },
        )
        service_class.return_value.request_primary_calendar_sync.assert_not_called()

    @patch("apps.bff.api.routers.calendar_router.CalendarWebhookSyncService")
    def test_google_webhook_endpoint_accepts_valid_notification(self, service_class):
        service_class.return_value.handle_notification.return_value = type(
            "WebhookResult",
            (),
            {"accepted": True, "sync_requested": True},
        )()

        response = cast(Any, self.client).post(
            "/api/v1/calendar/webhook/google",
            HTTP_HOST="localhost",
            **{
                "HTTP_X_GOOG_CHANNEL_ID": "channel-123",
                "HTTP_X_GOOG_CHANNEL_TOKEN": "secret-token",
                "HTTP_X_GOOG_RESOURCE_ID": "resource-456",
                "HTTP_X_GOOG_RESOURCE_STATE": "exists",
            },
        )

        self.assertEqual(response.status_code, 202)
        service_class.return_value.handle_notification.assert_called_once()

    @patch("apps.bff.api.routers.calendar_router.CalendarWebhookSyncService")
    def test_google_webhook_endpoint_rejects_invalid_notification(self, service_class):
        from apps.calendars.services.calendar_webhook_sync_service import (
            CalendarWebhookAuthenticationError,
        )

        service_class.return_value.handle_notification.side_effect = (
            CalendarWebhookAuthenticationError("Invalid Google calendar webhook notification.")
        )

        response = cast(Any, self.client).post(
            "/api/v1/calendar/webhook/google",
            HTTP_HOST="localhost",
            **{
                "HTTP_X_GOOG_CHANNEL_ID": "channel-123",
                "HTTP_X_GOOG_CHANNEL_TOKEN": "bad-token",
                "HTTP_X_GOOG_RESOURCE_ID": "resource-456",
                "HTTP_X_GOOG_RESOURCE_STATE": "exists",
            },
        )

        self.assertEqual(response.status_code, 401)
