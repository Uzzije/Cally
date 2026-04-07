from ninja import Schema


class ChatSessionResponseSchema(Schema):
    id: int
    title: str
    updated_at: str
