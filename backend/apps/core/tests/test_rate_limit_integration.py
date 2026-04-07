import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

User = get_user_model()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-rate-limit-integration",
        }
    },
)
class RateLimitIntegrationTests(TestCase):
    """Integration tests verifying django-ratelimit decorators fire through
    the full middleware stack and return proper 429 JSON responses.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="rl-test-user",
            email="rl-test@example.com",
            password="test-pass-123",
        )
        self.client.force_login(self.user)
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_auth_csrf_endpoint_is_not_rate_limited(self):
        for _ in range(50):
            response = self.client.get("/api/v1/auth/csrf")
            self.assertEqual(response.status_code, 200)

    @patch(
        "apps.chat.services.chat_turn_trigger_service.ChatTurnTriggerService.request_turn_processing"
    )
    def test_chat_message_post_returns_429_after_limit(self, mock_trigger):
        mock_trigger.return_value = None
        from apps.chat.services.chat_session_service import ChatSessionService

        session = ChatSessionService().create_session(self.user)
        url = f"/api/v1/chat/sessions/{session.id}/messages"

        hit_429 = False
        for i in range(15):
            response = self.client.post(
                url,
                data=json.dumps({"content": f"message {i}"}),
                content_type="application/json",
            )
            if response.status_code == 429:
                body = json.loads(response.content)
                self.assertIn("detail", body)
                self.assertIn("Retry-After", response)
                hit_429 = True
                break

        self.assertTrue(hit_429, "Expected a 429 response within 15 requests")

    @patch(
        "apps.calendars.services.calendar_sync_trigger_service.CalendarSyncTriggerService.request_primary_calendar_sync"
    )
    def test_calendar_sync_returns_429_after_limit(self, mock_sync):
        mock_sync.return_value = ["fake-event-id"]
        url = "/api/v1/calendar/sync"

        hit_429 = False
        for i in range(10):
            response = self.client.post(url)
            if response.status_code == 429:
                body = json.loads(response.content)
                self.assertIn("detail", body)
                hit_429 = True
                break

        self.assertTrue(hit_429, "Expected a 429 response within 10 requests")

    @patch(
        "apps.calendars.services.calendar_sync_trigger_service.CalendarSyncTriggerService.request_primary_calendar_sync"
    )
    def test_rate_limit_429_response_body_shape(self, mock_sync):
        mock_sync.return_value = ["fake-event-id"]
        url = "/api/v1/calendar/sync"

        last_response = None
        for i in range(10):
            last_response = self.client.post(url)
            if last_response.status_code == 429:
                break

        if last_response and last_response.status_code == 429:
            body = json.loads(last_response.content)
            self.assertIn("detail", body)
            self.assertIsInstance(body["detail"], str)
            self.assertIn("Retry-After", last_response)
        else:
            self.fail("Never received a 429 response")
