import logging

from django.contrib.auth import get_user_model
import inngest

from apps.calendars.inngest.client import inngest_client
from apps.calendars.services.calendar_sync_service import (
    CalendarSyncPrerequisiteError,
    CalendarSyncService,
)

logger = logging.getLogger(__name__)
User = get_user_model()


@inngest_client.create_function(
    fn_id="sync-primary-calendar",
    name="Sync Primary Calendar",
    retries=2,
    trigger=inngest.TriggerEvent(event="calendar.sync.requested"),
)
def sync_primary_calendar_function(ctx: inngest.Context) -> dict:
    user_id = ctx.event.data.get("user_id")
    if not user_id:
        raise ValueError("calendar.sync.requested event missing user_id")

    user = User.objects.get(pk=user_id)
    try:
        result = CalendarSyncService().sync_primary_calendar(user)
    except CalendarSyncPrerequisiteError as exc:
        logger.warning(
            "calendar.sync.skipped",
            extra={
                "user_id": user.id,
                "reason": str(exc),
            },
        )
        return {
            "status": "skipped",
            "code": exc.code,
            "detail": str(exc),
            "calendar_id": None,
            "event_count": 0,
            "sync_token_present": False,
            "last_synced_at": None,
        }

    logger.info(
        "calendar.sync.completed",
        extra={
            "user_id": user.id,
            "event_count": result.event_count,
            "sync_token_present": bool(result.sync_token),
        },
    )
    return {
        "status": "completed",
        "calendar_id": result.calendar_id,
        "event_count": result.event_count,
        "sync_token_present": bool(result.sync_token),
        "last_synced_at": result.last_synced_at,
    }
