import logging

import inngest

from apps.calendars.inngest.client import inngest_client
from apps.core.types import AuthenticatedUser

logger = logging.getLogger(__name__)


class CalendarSyncTriggerService:
    def __init__(self, client: inngest.Inngest | None = None) -> None:
        """Emit background sync requests (e.g. via Inngest) for calendar synchronization."""
        self.client = client or inngest_client

    def request_primary_calendar_sync(self, user: AuthenticatedUser) -> list[str]:
        """Request an async primary-calendar sync and return emitted event ids."""
        event = inngest.Event(
            name="calendar.sync.requested",
            data={
                "user_id": user.id,
                "email": user.email,
            },
        )
        event_ids = self.client.send_sync(event)
        logger.info(
            "calendar.sync.requested",
            extra={
                "user_id": user.id,
                "event_ids": event_ids,
            },
        )
        return event_ids
