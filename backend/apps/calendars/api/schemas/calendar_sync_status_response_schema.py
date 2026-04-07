from ninja import Schema


class CalendarSyncStatusResponseSchema(Schema):
    has_calendar: bool
    sync_state: str
    last_synced_at: str | None = None
    is_stale: bool
