import logging

import inngest

from apps.calendars.inngest.client import inngest_client

logger = logging.getLogger(__name__)


class TemporaryBlockedTimeTriggerService:
    def __init__(self, client: inngest.Inngest | None = None) -> None:
        """Emit background cleanup requests for expiring temporary blocked times."""
        self.client = client or inngest_client

    def request_expiry_cleanup(self, *, user_id: int, public_ids: list[str]) -> list[str]:
        """Request async expiry cleanup for the given blocked time ids, returning emitted event ids."""
        if not public_ids:
            return []

        event = inngest.Event(
            name="preferences.temp_blocked_times.created",
            data={
                "user_id": user_id,
                "public_ids": public_ids,
            },
        )
        event_ids = self.client.send_sync(event)
        logger.info(
            "preferences.temporary_blocked_times.cleanup_requested user_id=%s public_ids=%s event_ids=%s",
            user_id,
            public_ids,
            event_ids,
        )
        return event_ids
