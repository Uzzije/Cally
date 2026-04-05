from ninja import Schema


class CalendarSyncResponseSchema(Schema):
    accepted: bool
    event_ids: list[str]
