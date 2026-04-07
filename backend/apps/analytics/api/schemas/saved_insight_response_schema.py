from typing import Any

from ninja import Schema


class SavedInsightResponseSchema(Schema):
    id: str
    title: str
    summary_text: str
    chart_payload: dict[str, Any]
    created_at: str
    last_refreshed_at: str
    replaced_existing: bool = False
