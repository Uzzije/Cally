from typing import Any

from ninja import Schema


class ChatTurnResponseSchema(Schema):
    id: int
    status: str
    result_kind: str
    scope_decision: str
    failure_reason: str | None = None
    trace_events: list[dict[str, Any]]
    created_at: str
    completed_at: str | None = None
