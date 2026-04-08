from ninja import Schema


class CalendarResponseSchema(Schema):
    id: int
    name: str
    is_primary: bool
    timezone: str = ""
    last_synced_at: str | None = None
