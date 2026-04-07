import logging

import inngest

from apps.calendars.inngest.client import inngest_client

logger = logging.getLogger(__name__)


class ChatTurnTriggerService:
    def __init__(self, client: inngest.Inngest | None = None) -> None:
        self.client = client or inngest_client

    def request_turn_processing(self, *, turn) -> list[str]:
        event = inngest.Event(
            name="chat.turn.requested",
            data={
                "turn_id": turn.id,
                "session_id": turn.session_id,
                "user_id": turn.session.user_id,
                "correlation_id": turn.correlation_id,
            },
        )
        event_ids = self.client.send_sync(event)
        logger.info(
            "chat.turn.requested",
            extra={
                "turn_id": turn.id,
                "session_id": turn.session_id,
                "user_id": turn.session.user_id,
                "correlation_id": turn.correlation_id,
                "event_ids": event_ids,
            },
        )
        return event_ids
