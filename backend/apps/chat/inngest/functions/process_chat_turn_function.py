import logging

import inngest

from apps.calendars.inngest.client import inngest_client
from apps.chat.models.chat_turn import ChatTurn
from apps.chat.services.chat_turn_execution_service import ChatTurnExecutionService

logger = logging.getLogger(__name__)


@inngest_client.create_function(
    fn_id="process-chat-turn",
    name="Process Chat Turn",
    retries=2,
    trigger=inngest.TriggerEvent(event="chat.turn.requested"),
)
def process_chat_turn_function(ctx: inngest.Context) -> dict:
    turn_id = ctx.event.data.get("turn_id")
    if not turn_id:
        raise ValueError("chat.turn.requested event missing turn_id")

    turn = ChatTurn.objects.select_related(
        "session", "user_message", "assistant_message", "session__user"
    ).get(pk=turn_id)
    result_turn = ChatTurnExecutionService().process_turn(turn=turn)
    logger.info(
        "chat.turn.processed",
        extra={
            "turn_id": result_turn.id,
            "session_id": result_turn.session_id,
            "status": result_turn.status,
            "result_kind": result_turn.result_kind,
            "correlation_id": result_turn.correlation_id,
        },
    )
    return {
        "turn_id": result_turn.id,
        "status": result_turn.status,
        "result_kind": result_turn.result_kind,
    }
