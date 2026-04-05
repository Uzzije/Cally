from typing import Any

from ninja import Schema


class ChatMessageResponseSchema(Schema):
    id: int
    role: str
    content_blocks: list[dict[str, Any]]
    created_at: str

