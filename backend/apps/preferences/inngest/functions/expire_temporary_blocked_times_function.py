from __future__ import annotations

from datetime import timedelta

import inngest

from apps.calendars.inngest.client import inngest_client
from apps.preferences.services.temporary_blocked_time_service import TemporaryBlockedTimeService


@inngest_client.create_function(
    fn_id="expire-temporary-blocked-times",
    name="Expire Temporary Blocked Times",
    retries=1,
    trigger=inngest.TriggerEvent(event="preferences.temp_blocked_times.created"),
)
def expire_temporary_blocked_times_function(ctx: inngest.Context, step: inngest.StepSync) -> dict:
    public_ids = ctx.event.data.get("public_ids") or []
    if not isinstance(public_ids, list) or len(public_ids) == 0:
        raise ValueError("preferences.temp_blocked_times.created missing public_ids")

    step.sleep("wait-one-hour", timedelta(hours=1))
    expired_count = TemporaryBlockedTimeService().expire_by_public_ids(
        public_ids=[str(public_id) for public_id in public_ids]
    )
    return {
        "public_ids": public_ids,
        "expired_count": expired_count,
    }
