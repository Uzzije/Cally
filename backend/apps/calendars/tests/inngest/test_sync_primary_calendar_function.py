from datetime import timedelta
from typing import Any, cast
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase
from django.utils import timezone

from apps.accounts.services.google_oauth_credential_service import GoogleOAuthCredentialService
from apps.calendars.inngest.functions.sync_primary_calendar_function import (
    sync_primary_calendar_function,
)
from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event
from apps.calendars.services.calendar_sync_service import CalendarSyncService
from apps.calendars.services.google_calendar_payloads import (
    CalendarEventPayload,
    GoogleCalendarDescriptor,
)

User = get_user_model()


class _FakeEvent:
    def __init__(self, user_id: int | None):
        self.data = {"user_id": user_id}


class _FakeContext:
    def __init__(self, user_id: int | None):
        self.event = _FakeEvent(user_id)


class _FakeGoogleCalendarClient:
    def get_primary_calendar(self, user):
        return GoogleCalendarDescriptor(
            google_calendar_id="primary-calendar-id",
            name="Primary",
            is_primary=True,
            color="#C05746",
            timezone="America/New_York",
        )

    def list_events(self, user, *, calendar_id: str, sync_token: str | None = None):
        start_time = timezone.now()
        return (
            [
                CalendarEventPayload(
                    google_event_id="google-event-1",
                    title="Design Review",
                    description="Roadmap review",
                    start_time=start_time,
                    end_time=start_time + timedelta(hours=1),
                    timezone="America/New_York",
                    location="Zoom",
                    status="confirmed",
                    attendees=[{"email": "teammate@example.com"}],
                    organizer_email="owner@example.com",
                    is_all_day=False,
                )
            ],
            "sync-token-1",
        )


class SyncPrimaryCalendarFunctionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="calendar-sync-function@example.com",
            password="test-pass-123",
        )
        site = Site.objects.get_current()
        social_app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="client-id",
            secret="client-secret",
        )
        social_app.sites.add(site)
        social_account = SocialAccount.objects.create(
            user=self.user,
            provider="google",
            uid="google-user-1",
        )
        SocialToken.objects.create(
            app=social_app,
            account=social_account,
            token="token",
            token_secret="secret",
        )
        GoogleOAuthCredentialService().get_decrypted_credential(self.user)

    def test_function_syncs_primary_calendar_into_database(self):
        handler = cast(Any, sync_primary_calendar_function)._handler
        service = CalendarSyncService(client=_FakeGoogleCalendarClient())

        with patch(
            "apps.calendars.inngest.functions.sync_primary_calendar_function.CalendarSyncService",
            return_value=service,
        ):
            result = handler(_FakeContext(self.user.id))

        calendar = Calendar.objects.get(user=self.user, google_calendar_id="primary-calendar-id")
        event = Event.objects.get(calendar=calendar, google_event_id="google-event-1")

        self.assertEqual(calendar.name, "Primary")
        self.assertEqual(calendar.sync_token, "sync-token-1")
        self.assertEqual(event.title, "Design Review")
        self.assertEqual(result["calendar_id"], calendar.id)
        self.assertEqual(result["event_count"], 1)
        self.assertTrue(result["sync_token_present"])
        self.assertEqual(result["last_synced_at"], calendar.last_synced_at.isoformat())

    def test_function_requires_user_id_in_event_payload(self):
        handler = cast(Any, sync_primary_calendar_function)._handler

        with self.assertRaisesMessage(ValueError, "calendar.sync.requested event missing user_id"):
            handler(_FakeContext(None))
