from ninja import Schema


class TemporaryBlockedTimeEntryRequestSchema(Schema):
    label: str
    date: str
    start: str
    end: str
    source: str


class TemporaryBlockedTimeBulkCreateRequestSchema(Schema):
    timezone: str
    entries: list[TemporaryBlockedTimeEntryRequestSchema]
