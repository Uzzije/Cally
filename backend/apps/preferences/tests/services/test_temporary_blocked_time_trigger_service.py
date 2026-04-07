from unittest.mock import Mock

from django.test import TestCase

from apps.preferences.services.temporary_blocked_time_trigger_service import (
    TemporaryBlockedTimeTriggerService,
)


class TemporaryBlockedTimeTriggerServiceTests(TestCase):
    def test_request_expiry_cleanup_sends_inngest_event(self):
        client = Mock()
        client.send_sync.return_value = ["event-id-1"]

        event_ids = TemporaryBlockedTimeTriggerService(client=client).request_expiry_cleanup(
            user_id=7,
            public_ids=["temp-1", "temp-2"],
        )

        self.assertEqual(event_ids, ["event-id-1"])
        sent_event = client.send_sync.call_args.args[0]
        self.assertEqual(sent_event.name, "preferences.temp_blocked_times.created")
        self.assertEqual(sent_event.data["user_id"], 7)
        self.assertEqual(sent_event.data["public_ids"], ["temp-1", "temp-2"])
