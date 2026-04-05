from datetime import timedelta

from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase
from django.utils import timezone

from apps.calendars.models.calendar import Calendar
from apps.calendars.models.event import Event
from apps.calendars.services.google_calendar_payloads import CalendarEventPayload, GoogleCalendarDescriptor
from apps.calendars.services.calendar_sync_service import CalendarSyncError, CalendarSyncService


User = get_user_model()


class FakeGoogleCalendarClient:
    def __init__(self, *, event_title: str = "Design Review", sync_token: str = "sync-token-1") -> None:
        self.event_title = event_title
        self.sync_token = sync_token
        self.calls: list[dict] = []

    def get_primary_calendar(self, user):
        self.calls.append({"method": "get_primary_calendar", "user_id": user.id})
        return GoogleCalendarDescriptor(
            google_calendar_id="primary-calendar-id",
            name="Primary",
            is_primary=True,
            color="#C05746",
        )

    def list_events(self, user, *, calendar_id: str, sync_token: str | None = None):
        self.calls.append(
            {
                "method": "list_events",
                "user_id": user.id,
                "calendar_id": calendar_id,
                "sync_token": sync_token,
            }
        )
        start_time = timezone.now()
        return (
            [
                CalendarEventPayload(
                    google_event_id="google-event-1",
                    title=self.event_title,
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
            self.sync_token,
        )


class ErroringGoogleCalendarClient(FakeGoogleCalendarClient):
    def get_primary_calendar(self, user):
        raise RuntimeError("google error")

    def list_events(self, user, *, calendar_id: str, sync_token: str | None = None):
        raise RuntimeError("google error")


class EventListErroringGoogleCalendarClient(FakeGoogleCalendarClient):
    def list_events(self, user, *, calendar_id: str, sync_token: str | None = None):
        raise RuntimeError("google error")


class CalendarSyncServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="calendar-sync@example.com",
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

    def test_first_sync_creates_primary_calendar_and_events(self):
        service = CalendarSyncService(client=FakeGoogleCalendarClient())

        result = service.sync_primary_calendar(self.user)

        calendar = Calendar.objects.get(user=self.user, google_calendar_id="primary-calendar-id")
        event = Event.objects.get(calendar=calendar, google_event_id="google-event-1")
        self.assertTrue(calendar.is_primary)
        self.assertEqual(event.title, "Design Review")
        self.assertEqual(result.event_count, 1)
        self.assertEqual(calendar.sync_token, "sync-token-1")

    def test_repeat_sync_updates_existing_event_without_duplication(self):
        initial_service = CalendarSyncService(client=FakeGoogleCalendarClient(event_title="Original Title"))
        initial_service.sync_primary_calendar(self.user)

        repeat_service = CalendarSyncService(
            client=FakeGoogleCalendarClient(event_title="Updated Title", sync_token="sync-token-2")
        )
        repeat_service.sync_primary_calendar(self.user)

        calendar = Calendar.objects.get(user=self.user, google_calendar_id="primary-calendar-id")
        self.assertEqual(Event.objects.filter(calendar=calendar).count(), 1)
        self.assertEqual(
            Event.objects.get(calendar=calendar, google_event_id="google-event-1").title,
            "Updated Title",
        )
        self.assertEqual(calendar.sync_token, "sync-token-2")

    def test_repeat_sync_passes_existing_sync_token_to_client(self):
        initial_service = CalendarSyncService(client=FakeGoogleCalendarClient(sync_token="sync-token-1"))
        initial_service.sync_primary_calendar(self.user)
        client = FakeGoogleCalendarClient(sync_token="sync-token-2")

        CalendarSyncService(client=client).sync_primary_calendar(self.user)

        self.assertEqual(client.calls[-1]["sync_token"], "sync-token-1")

    def test_missing_google_token_raises_domain_error(self):
        SocialToken.objects.all().delete()
        service = CalendarSyncService(client=FakeGoogleCalendarClient())

        with self.assertRaises(CalendarSyncError):
            service.sync_primary_calendar(self.user)

    def test_google_failure_raises_typed_sync_error(self):
        service = CalendarSyncService(client=ErroringGoogleCalendarClient())

        with self.assertRaises(CalendarSyncError):
            service.sync_primary_calendar(self.user)

    def test_google_event_fetch_failure_raises_typed_sync_error(self):
        service = CalendarSyncService(client=EventListErroringGoogleCalendarClient())

        with self.assertRaises(CalendarSyncError):
            service.sync_primary_calendar(self.user)
