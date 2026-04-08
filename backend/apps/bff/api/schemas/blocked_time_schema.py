from ninja import Schema


class BlockedTimeSchema(Schema):
    id: str | None = None
    label: str
    days: list[str]
    start: str
    end: str
