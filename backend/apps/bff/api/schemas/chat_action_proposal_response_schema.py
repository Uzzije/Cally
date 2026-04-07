from typing import Any

from ninja import Schema


class ChatActionProposalResponseSchema(Schema):
    id: str
    status: str
    action_type: str
    summary: str
    details: dict[str, Any]
    status_detail: str | None = None
    result: dict[str, Any] | None = None
