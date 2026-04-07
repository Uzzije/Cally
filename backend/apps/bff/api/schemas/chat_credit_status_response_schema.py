from ninja import Schema


class ChatCreditStatusResponseSchema(Schema):
    limit: int
    used: int
    remaining: int
    usage_date: str
