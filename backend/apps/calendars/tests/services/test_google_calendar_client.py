from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.calendars.services.google_calendar_client import GoogleCalendarClient, GoogleCalendarClientError


class GoogleCalendarClientTests(SimpleTestCase):
    @patch("apps.calendars.services.google_calendar_client.requests.get")
    def test_initial_sync_follows_pagination_until_next_sync_token_is_present(self, requests_get):
        client = GoogleCalendarClient()
        client._get_headers = Mock(return_value={"Authorization": "Bearer token"})  # type: ignore[attr-defined]

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

        requests_get.side_effect = [first_response, second_response]

        events, next_sync_token = client.list_events(
            user=object(),
            calendar_id="primary-calendar-id",
            sync_token=None,
        )

        self.assertEqual(len(events), 2)
        self.assertEqual(next_sync_token, "sync-token-1")
        self.assertEqual(requests_get.call_count, 2)
        self.assertEqual(requests_get.call_args_list[1].kwargs["params"]["pageToken"], "page-2")

    @patch("apps.calendars.services.google_calendar_client.requests.get")
    def test_incremental_sync_requires_sync_token_in_final_response(self, requests_get):
        client = GoogleCalendarClient()
        client._get_headers = Mock(return_value={"Authorization": "Bearer token"})  # type: ignore[attr-defined]

        response = Mock()
        response.ok = True
        response.json.return_value = {
            "items": [],
        }
        requests_get.return_value = response

        with self.assertRaises(GoogleCalendarClientError):
            client.list_events(
                user=object(),
                calendar_id="primary-calendar-id",
                sync_token="existing-sync-token",
            )

    @patch("apps.calendars.services.google_calendar_client.requests.get")
    def test_initial_bounded_sync_allows_missing_sync_token(self, requests_get):
        client = GoogleCalendarClient()
        client._get_headers = Mock(return_value={"Authorization": "Bearer token"})  # type: ignore[attr-defined]

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
        requests_get.return_value = response

        events, next_sync_token = client.list_events(
            user=object(),
            calendar_id="primary-calendar-id",
            sync_token=None,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(next_sync_token, "")
