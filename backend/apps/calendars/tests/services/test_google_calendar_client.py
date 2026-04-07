from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.calendars.services.google_calendar_client import (
    GoogleCalendarClient,
    GoogleCalendarClientError,
)
from apps.accounts.services.google_oauth_credential_service import DecryptedGoogleOAuthCredential


class GoogleCalendarClientTests(SimpleTestCase):
    @patch("apps.calendars.services.google_calendar_client.requests.request")
    def test_initial_sync_follows_pagination_until_next_sync_token_is_present(
        self, requests_request
    ):
        client = GoogleCalendarClient()
        cast(Any, client)._get_headers = Mock(return_value={"Authorization": "Bearer token"})

        first_response = Mock()
        first_response.ok = True
        first_response.json.return_value = {
            "items": [
                {
                    "id": "evt-1",
                    "summary": "First page event",
                    "start": {"dateTime": "2026-04-06T14:00:00Z"},
                    "end": {"dateTime": "2026-04-06T15:00:00Z"},
                }
            ],
            "nextPageToken": "page-2",
        }

        second_response = Mock()
        second_response.ok = True
        second_response.json.return_value = {
            "items": [
                {
                    "id": "evt-2",
                    "summary": "Second page event",
                    "start": {"dateTime": "2026-04-07T14:00:00Z"},
                    "end": {"dateTime": "2026-04-07T15:00:00Z"},
                }
            ],
            "nextSyncToken": "sync-token-1",
        }

        requests_request.side_effect = [first_response, second_response]

        events, next_sync_token = client.list_events(
            user=object(),
            calendar_id="primary-calendar-id",
            sync_token=None,
        )

        self.assertEqual(len(events), 2)
        self.assertEqual(next_sync_token, "sync-token-1")
        self.assertEqual(requests_request.call_count, 2)
        self.assertEqual(requests_request.call_args_list[1].kwargs["params"]["pageToken"], "page-2")

    @patch("apps.calendars.services.google_calendar_client.requests.request")
    def test_incremental_sync_requires_sync_token_in_final_response(self, requests_request):
        client = GoogleCalendarClient()
        cast(Any, client)._get_headers = Mock(return_value={"Authorization": "Bearer token"})

        response = Mock()
        response.ok = True
        response.json.return_value = {
            "items": [],
        }
        requests_request.return_value = response

        with self.assertRaises(GoogleCalendarClientError):
            client.list_events(
                user=object(),
                calendar_id="primary-calendar-id",
                sync_token="existing-sync-token",
            )

    @patch("apps.calendars.services.google_calendar_client.requests.request")
    def test_initial_bounded_sync_allows_missing_sync_token(self, requests_request):
        client = GoogleCalendarClient()
        cast(Any, client)._get_headers = Mock(return_value={"Authorization": "Bearer token"})

        response = Mock()
        response.ok = True
        response.json.return_value = {
            "items": [
                {
                    "id": "evt-1",
                    "summary": "Bounded event",
                    "start": {"dateTime": "2026-04-06T14:00:00Z"},
                    "end": {"dateTime": "2026-04-06T15:00:00Z"},
                }
            ],
        }
        requests_request.return_value = response

        events, next_sync_token = client.list_events(
            user=object(),
            calendar_id="primary-calendar-id",
            sync_token=None,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(next_sync_token, "")

    @patch("apps.calendars.services.google_calendar_client.requests.request")
    def test_get_free_busy_returns_parsed_busy_ranges_by_attendee(self, requests_request):
        client = GoogleCalendarClient()
        cast(Any, client)._get_headers = Mock(return_value={"Authorization": "Bearer token"})

        response = Mock()
        response.ok = True
        response.json.return_value = {
            "calendars": {
                "joe@example.com": {
                    "busy": [
                        {
                            "start": "2026-04-07T13:00:00+00:00",
                            "end": "2026-04-07T14:00:00+00:00",
                        }
                    ]
                }
            }
        }
        requests_request.return_value = response

        result = client.get_free_busy(
            user=object(),
            attendee_emails=["joe@example.com"],
            time_min=self._dt("2026-04-07T09:00:00+00:00"),
            time_max=self._dt("2026-04-07T17:00:00+00:00"),
        )

        self.assertEqual(len(result["joe@example.com"]), 1)
        self.assertEqual(result["joe@example.com"][0][0].isoformat(), "2026-04-07T13:00:00+00:00")

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {
                "APPS": [
                    {
                        "client_id": "test-client-id",
                        "secret": "test-client-secret",
                    }
                ]
            }
        }
    )
    @patch("apps.calendars.services.google_calendar_client.requests.post")
    def test_get_headers_refreshes_expired_access_token(self, requests_post):
        credential_service = Mock()
        credential_service.get_decrypted_credential.return_value = DecryptedGoogleOAuthCredential(
            access_token="expired-token",
            refresh_token="refresh-token",
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        client = GoogleCalendarClient(credential_service=credential_service)

        response = Mock()
        response.ok = True
        response.json.return_value = {"access_token": "fresh-token", "expires_in": 3600}
        requests_post.return_value = response

        headers = client._get_headers(user=object())

        self.assertEqual(headers["Authorization"], "Bearer fresh-token")
        credential_service.update_access_token.assert_called_once()

    @patch("apps.calendars.services.google_calendar_client.requests.request")
    def test_request_retries_once_after_google_unauthorized(self, requests_request):
        user = object()
        credential_service = Mock()
        credential = DecryptedGoogleOAuthCredential(
            access_token="expired-token",
            refresh_token="refresh-token",
            expires_at=None,
        )
        credential_service.get_decrypted_credential.return_value = credential
        client = GoogleCalendarClient(credential_service=credential_service)
        cast(Any, client)._get_headers = Mock(
            side_effect=[
                {"Authorization": "Bearer expired-token"},
                {"Authorization": "Bearer fresh-token"},
            ]
        )
        cast(Any, client)._refresh_credential = Mock(return_value=credential)

        first_response = Mock(status_code=401)
        second_response = Mock(status_code=200)
        requests_request.side_effect = [first_response, second_response]

        response = client._request("GET", "https://example.com", user=user, timeout=20)

        self.assertEqual(response.status_code, 200)
        cast(Any, client)._refresh_credential.assert_called_once_with(user=user)
        self.assertEqual(requests_request.call_count, 2)

    @patch("apps.calendars.services.google_calendar_client.requests.request")
    def test_watch_calendar_registers_google_push_channel(self, requests_request):
        client = GoogleCalendarClient()
        cast(Any, client)._get_headers = Mock(return_value={"Authorization": "Bearer token"})

        response = Mock()
        response.ok = True
        response.json.return_value = {
            "id": "channel-123",
            "resourceId": "resource-456",
            "expiration": "1770000000000",
        }
        requests_request.return_value = response

        watch = client.watch_calendar(
            user=object(),
            calendar_id="primary-calendar-id",
            webhook_address="https://example.com/api/v1/calendar/webhook/google",
            channel_id="channel-123",
            channel_token="secret-token",
        )

        self.assertEqual(watch.channel_id, "channel-123")
        self.assertEqual(watch.resource_id, "resource-456")
        request_args = requests_request.call_args.args
        request_kwargs = requests_request.call_args.kwargs
        self.assertEqual(request_args[0], "POST")
        self.assertEqual(
            request_args[1],
            "https://www.googleapis.com/calendar/v3/calendars/primary-calendar-id/events/watch",
        )
        self.assertEqual(
            request_kwargs["json"],
            {
                "id": "channel-123",
                "type": "web_hook",
                "address": "https://example.com/api/v1/calendar/webhook/google",
                "token": "secret-token",
                "params": {"ttl": "604800"},
            },
        )

    @patch("apps.calendars.services.google_calendar_client.requests.request")
    def test_watch_calendar_raises_typed_error_when_google_rejects_request(self, requests_request):
        client = GoogleCalendarClient()
        cast(Any, client)._get_headers = Mock(return_value={"Authorization": "Bearer token"})

        response = Mock()
        response.ok = False
        response.status_code = 400
        response.text = "bad request"
        requests_request.return_value = response

        with self.assertRaises(GoogleCalendarClientError):
            client.watch_calendar(
                user=object(),
                calendar_id="primary-calendar-id",
                webhook_address="https://example.com/api/v1/calendar/webhook/google",
                channel_id="channel-123",
                channel_token="secret-token",
            )

    @patch("apps.calendars.services.google_calendar_client.requests.request")
    def test_stop_channel_posts_channel_shutdown_request(self, requests_request):
        client = GoogleCalendarClient()
        cast(Any, client)._get_headers = Mock(return_value={"Authorization": "Bearer token"})

        response = Mock()
        response.ok = True
        requests_request.return_value = response

        client.stop_channel(
            user=object(),
            channel_id="channel-123",
            resource_id="resource-456",
        )

        request_args = requests_request.call_args.args
        request_kwargs = requests_request.call_args.kwargs
        self.assertEqual(request_args[0], "POST")
        self.assertEqual(request_args[1], "https://www.googleapis.com/calendar/v3/channels/stop")
        self.assertEqual(
            request_kwargs["json"],
            {
                "id": "channel-123",
                "resourceId": "resource-456",
            },
        )

    def _dt(self, value: str):
        from django.utils.dateparse import parse_datetime

        parsed = parse_datetime(value)
        assert parsed is not None
        return parsed
