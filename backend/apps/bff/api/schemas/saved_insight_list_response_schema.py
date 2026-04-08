from ninja import Schema

from apps.bff.api.schemas.saved_insight_policy_schema import SavedInsightPolicySchema
from apps.bff.api.schemas.saved_insight_response_schema import SavedInsightResponseSchema


class SavedInsightListResponseSchema(Schema):
    items: list[SavedInsightResponseSchema]
    policy: SavedInsightPolicySchema
