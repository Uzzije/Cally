from __future__ import annotations

import logging
from datetime import timedelta

from allauth.socialaccount.models import SocialToken
from django.utils import timezone
import requests

from apps.calendars.services.google_calendar_payloads import (
    CalendarEventPayload,
    GoogleCalendarDescriptor,
)
from apps.calendars.services.google_calendar_event_normalizer import normalize_google_event


logger = logging.getLogger(__name__)


class GoogleCalendarClientError(Exception):
    pass


class GoogleCalendarClient:
    base_url = "https://www.googleapis.com/calendar/v3"

    def _get_social_token(self, user) -> SocialToken:
        social_token = (
            SocialToken.objects.select_related("account")
            .filter(account__user=user, account__provider="google")
            .first()
        )
        if social_token is None or not social_token.token:
            raise GoogleCalendarClientError("Google access token is not available.")

        return social_token

    def _get_headers(self, user) -> dict[str, str]:
        social_token = self._get_social_token(user)
        return {"Authorization": f"Bearer {social_token.token}"}

    def _raise_for_google_error(self, *, operation: str, response: requests.Response) -> None:
        response_preview = response.text[:500]
        logger.warning(
            "Google Calendar API request failed",
            extra={
                "operation": operation,
                "status_code": response.status_code,
                "response_preview": response_preview,
            },
        )
        raise GoogleCalendarClientError(
            f"{operation} failed with Google Calendar API status {response.status_code}."
        )

    def get_primary_calendar(self, user) -> GoogleCalendarDescriptor:
        response = requests.get(
            f"{self.base_url}/users/me/calendarList",
            headers=self._get_headers(user),
            timeout=20,
        )
        if not response.ok:
            self._raise_for_google_error(
                operation="Fetch primary calendar list",
                response=response,
            )

        items = response.json().get("items", [])
        primary_calendar = next((item for item in items if item.get("primary")), None)
        if primary_calendar is None:
            raise GoogleCalendarClientError("Primary Google calendar was not found.")

        return GoogleCalendarDescriptor(
            google_calendar_id=primary_calendar["id"],
            name=primary_calendar.get("summaryOverride")
            or primary_calendar.get("summary")
            or "Primary",
            is_primary=True,
            color=primary_calendar.get("backgroundColor") or "",
        )

    def list_events(self, user, *, calendar_id: str, sync_token: str | None = None) -> tuple[list[CalendarEventPayload], str]:
        params: dict[str, str] = {
            "singleEvents": "true",
            "showDeleted": "false",
            "maxResults": "2500",
        }
        if sync_token:
            params["syncToken"] = sync_token
        else:
            now = timezone.now()
            params["timeMin"] = (now - timedelta(days=90)).isoformat()
            params["timeMax"] = (now + timedelta(days=180)).isoformat()
            params["orderBy"] = "startTime"

        all_items: list[dict] = []
        next_sync_token: str | None = None
        page_token: str | None = None

        while True:
            request_params = dict(params)
            if page_token:
                request_params["pageToken"] = page_token

            response = requests.get(
                f"{self.base_url}/calendars/{calendar_id}/events",
                headers=self._get_headers(user),
                params=request_params,
                timeout=20,
            )
            if not response.ok:
                self._raise_for_google_error(
                    operation="Fetch calendar events",
                    response=response,
                )

            payload = response.json()
            all_items.extend(payload.get("items", []))
            next_sync_token = payload.get("nextSyncToken") or next_sync_token
            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        if not next_sync_token:
            if sync_token is None:
                logger.info(
                    "Google Calendar bounded initial sync completed without nextSyncToken; falling back to full-range resyncs.",
                    extra={
                        "calendar_id": calendar_id,
                        "event_count": len(all_items),
                    },
                )
                return [
                    normalize_google_event(item)
                    for item in all_items
                    if item.get("status") != "cancelled"
                ], ""
            raise GoogleCalendarClientError("Google calendar sync token was not returned.")

        normalized_events = [
            normalize_google_event(item)
            for item in all_items
            if item.get("status") != "cancelled"
        ]
        return normalized_events, next_sync_token
