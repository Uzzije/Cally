from ninja import Schema


class ChatSubmitMessageRequestSchema(Schema):
    content: str
