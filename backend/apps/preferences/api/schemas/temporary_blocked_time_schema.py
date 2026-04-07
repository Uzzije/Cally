from ninja import Schema


class TemporaryBlockedTimeSchema(Schema):
    id: str
    label: str
    date: str
    start: str
    end: str
    timezone: str
    source: str
    created_at: str
    expires_at: str
