from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone as datetime_timezone

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import requests

from apps.accounts.services.google_oauth_credential_service import (
    DecryptedGoogleOAuthCredential,
    GoogleOAuthCredentialError,
    GoogleOAuthCredentialService,
)
from apps.calendars.services.google_calendar_payloads import (
    CalendarEventPayload,
    GoogleCalendarDescriptor,
    GoogleCalendarWatchSubscription,
)
from apps.calendars.services.google_calendar_event_normalizer import normalize_google_event
from apps.core.types import AuthenticatedUser

logger = logging.getLogger(__name__)


class GoogleCalendarClientError(Exception):
    pass


class GoogleCalendarClient:
    base_url = "https://www.googleapis.com/calendar/v3"
    token_url = "https://oauth2.googleapis.com/token"

    def __init__(self, credential_service: GoogleOAuthCredentialService | None = None) -> None:
        self.credential_service = credential_service or GoogleOAuthCredentialService()

    def _get_valid_credential(self, user: AuthenticatedUser) -> DecryptedGoogleOAuthCredential:
        credential = self._get_credential(user)
        if self._token_needs_refresh(credential):
            return self._refresh_credential(user=user)
        return credential

    def _get_headers(self, user: AuthenticatedUser) -> dict[str, str]:
        credential = self._get_valid_credential(user)
        return {"Authorization": f"Bearer {credential.access_token}"}

    def _get_credential(self, user: AuthenticatedUser) -> DecryptedGoogleOAuthCredential:
        try:
            return self.credential_service.get_decrypted_credential(user)
        except GoogleOAuthCredentialError as exc:
            raise GoogleCalendarClientError(str(exc)) from exc

    def _token_needs_refresh(self, credential: DecryptedGoogleOAuthCredential) -> bool:
        expires_at = credential.expires_at
        if expires_at is None:
            return False
        return expires_at <= timezone.now() + timedelta(minutes=1)

    def _refresh_credential(self, *, user: AuthenticatedUser) -> DecryptedGoogleOAuthCredential:
        credential = self._get_credential(user)
        refresh_token = credential.refresh_token
        client_id = (
            getattr(settings, "SOCIALACCOUNT_PROVIDERS", {})
            .get("google", {})
            .get("APPS", [{}])[0]
            .get("client_id")
        )
        client_secret = (
            getattr(settings, "SOCIALACCOUNT_PROVIDERS", {})
            .get("google", {})
            .get("APPS", [{}])[0]
            .get("secret")
        )

        if not refresh_token:
            raise GoogleCalendarClientError("Google refresh token is not available.")
        if not client_id or not client_secret:
            raise GoogleCalendarClientError("Google OAuth app credentials are not configured.")

        response = requests.post(
            self.token_url,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=20,
        )
        if not response.ok:
            self._raise_for_google_error(operation="Refresh Google access token", response=response)

        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise GoogleCalendarClientError(
                "Google refresh response did not include an access token."
            )

        expires_in = payload.get("expires_in")
        expires_at = credential.expires_at
        if isinstance(expires_in, int):
            expires_at = timezone.now() + timedelta(seconds=expires_in)
        self.credential_service.update_access_token(
            user,
            access_token=str(access_token),
            expires_at=expires_at,
        )
        return DecryptedGoogleOAuthCredential(
            access_token=str(access_token),
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

    def _request(
        self,
        method: str,
        url: str,
        *,
        user: AuthenticatedUser,
        retry_on_unauthorized: bool = True,
        **kwargs,
    ) -> requests.Response:
        extra_headers = kwargs.pop("headers", {})
        response = requests.request(
            method,
            url,
            headers=self._get_headers(user) | extra_headers,
            **kwargs,
        )
        if response.status_code == 401 and retry_on_unauthorized:
            credential = self._get_credential(user)
            if credential.refresh_token:
                self._refresh_credential(user=user)
                return self._request(
                    method,
                    url,
                    user=user,
                    retry_on_unauthorized=False,
                    headers=extra_headers,
                    **kwargs,
                )
        return response

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

    def get_primary_calendar(self, user: AuthenticatedUser) -> GoogleCalendarDescriptor:
        response = self._request(
            "GET",
            f"{self.base_url}/users/me/calendarList",
            user=user,
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
            timezone=primary_calendar.get("timeZone") or "",
        )

    def create_event(
        self,
        user: AuthenticatedUser,
        *,
        calendar_id: str,
        title,
        start_time,
        end_time,
        timezone_name: str,
        attendee_emails: list[str] | None = None,
        description: str = "",
        location: str = "",
    ) -> CalendarEventPayload:
        payload: dict[str, object] = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": timezone_name,
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": timezone_name,
            },
        }
        attendees = [
            {"email": attendee_email}
            for attendee_email in (attendee_emails or [])
            if attendee_email
        ]
        if attendees:
            payload["attendees"] = attendees

        response = self._request(
            "POST",
            f"{self.base_url}/calendars/{calendar_id}/events",
            user=user,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        if not response.ok:
            self._raise_for_google_error(
                operation="Create calendar event",
                response=response,
            )

        return normalize_google_event(response.json())

    def get_free_busy(
        self,
        user: AuthenticatedUser,
        *,
        attendee_emails: list[str],
        time_min: datetime,
        time_max: datetime,
    ) -> dict[str, list[tuple[datetime, datetime]]]:
        if not attendee_emails:
            return {}

        response = self._request(
            "POST",
            f"{self.base_url}/freeBusy",
            user=user,
            headers={"Content-Type": "application/json"},
            json={
                "timeMin": time_min.isoformat(),
                "timeMax": time_max.isoformat(),
                "items": [{"id": attendee_email} for attendee_email in attendee_emails],
            },
            timeout=20,
        )
        if not response.ok:
            self._raise_for_google_error(
                operation="Fetch attendee free busy",
                response=response,
            )

        busy_by_attendee: dict[str, list[tuple[datetime, datetime]]] = {}
        calendars = response.json().get("calendars", {})
        if not isinstance(calendars, dict):
            return busy_by_attendee

        for attendee_email, payload in calendars.items():
            busy_blocks = payload.get("busy", []) if isinstance(payload, dict) else []
            parsed_busy_blocks: list[tuple[datetime, datetime]] = []
            for block in busy_blocks:
                if not isinstance(block, dict):
                    continue
                start = parse_datetime(str(block.get("start")))
                end = parse_datetime(str(block.get("end")))
                if start is None or end is None or start >= end:
                    continue
                parsed_busy_blocks.append((start, end))
            busy_by_attendee[str(attendee_email).lower()] = parsed_busy_blocks

        return busy_by_attendee

    def list_events(
        self,
        user: AuthenticatedUser,
        *,
        calendar_id: str,
        sync_token: str | None = None,
    ) -> tuple[list[CalendarEventPayload], str]:
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

            response = self._request(
                "GET",
                f"{self.base_url}/calendars/{calendar_id}/events",
                user=user,
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
            normalize_google_event(item) for item in all_items if item.get("status") != "cancelled"
        ]
        return normalized_events, next_sync_token

    def watch_calendar(
        self,
        user: AuthenticatedUser,
        *,
        calendar_id: str,
        webhook_address: str,
        channel_id: str,
        channel_token: str,
    ) -> GoogleCalendarWatchSubscription:
        payload: dict[str, object] = {
            "id": channel_id,
            "type": "web_hook",
            "address": webhook_address,
            "token": channel_token,
        }
        ttl_seconds = getattr(settings, "GOOGLE_CALENDAR_WEBHOOK_TTL_SECONDS", 0)
        if ttl_seconds:
            payload["params"] = {"ttl": str(ttl_seconds)}

        response = self._request(
            "POST",
            f"{self.base_url}/calendars/{calendar_id}/events/watch",
            user=user,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        if not response.ok:
            self._raise_for_google_error(
                operation="Register calendar watch",
                response=response,
            )

        response_payload = response.json()
        resource_id = response_payload.get("resourceId")
        if not resource_id:
            raise GoogleCalendarClientError("Google watch response did not include a resourceId.")

        return GoogleCalendarWatchSubscription(
            channel_id=str(response_payload.get("id") or channel_id),
            resource_id=str(resource_id),
            expires_at=self._parse_google_expiration(response_payload.get("expiration")),
        )

    def _parse_google_expiration(self, raw_expiration: object) -> datetime | None:
        if raw_expiration in (None, ""):
            return None

        try:
            expiration_ms = int(str(raw_expiration))
        except (TypeError, ValueError):
            raise GoogleCalendarClientError(
                "Google watch response included an invalid expiration value."
            ) from None

        return datetime.fromtimestamp(expiration_ms / 1000, tz=datetime_timezone.utc)

    def stop_channel(self, user: AuthenticatedUser, *, channel_id: str, resource_id: str) -> None:
        response = self._request(
            "POST",
            f"{self.base_url}/channels/stop",
            user=user,
            headers={"Content-Type": "application/json"},
            json={
                "id": channel_id,
                "resourceId": resource_id,
            },
            timeout=20,
        )
        if not response.ok:
            self._raise_for_google_error(
                operation="Stop calendar watch channel",
                response=response,
            )
