from ninja import Schema


class CalendarWebhookResponseSchema(Schema):
    accepted: bool
    sync_requested: bool
