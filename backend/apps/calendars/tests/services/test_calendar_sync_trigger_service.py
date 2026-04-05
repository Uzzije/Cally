from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.calendars.services.calendar_sync_trigger_service import CalendarSyncTriggerService


User = get_user_model()


class CalendarSyncTriggerServiceTests(TestCase):
    def test_request_primary_calendar_sync_sends_inngest_event(self):
        user = User.objects.create_user(
            username="ignored",
            email="trigger@example.com",
            password="test-pass-123",
        )
        client = Mock()
        client.send_sync.return_value = ["event-id-1"]

        service = CalendarSyncTriggerService(client=client)

        event_ids = service.request_primary_calendar_sync(user)

        self.assertEqual(event_ids, ["event-id-1"])
        sent_event = client.send_sync.call_args.args[0]
        self.assertEqual(sent_event.name, "calendar.sync.requested")
        self.assertEqual(sent_event.data["user_id"], user.id)
