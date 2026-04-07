from ninja import Router

from apps.core.api.auth import session_auth
from apps.analytics.api.schemas.delete_saved_insight_response_schema import (
    DeleteSavedInsightResponseSchema,
)
from apps.analytics.api.schemas.error_response_schema import ErrorResponseSchema
from apps.analytics.api.schemas.saved_insight_list_response_schema import (
    SavedInsightListResponseSchema,
)
from apps.analytics.api.schemas.saved_insight_policy_schema import SavedInsightPolicySchema
from apps.analytics.api.schemas.saved_insight_request_schema import SavedInsightRequestSchema
from apps.analytics.api.schemas.saved_insight_response_schema import SavedInsightResponseSchema
from apps.analytics.services.saved_insight_service import (
    SavedInsightNotFoundError,
    SavedInsightService,
    SavedInsightValidationError,
)

router = Router(tags=["analytics"], auth=session_auth)


def _serialize_saved_insight(
    insight, *, replaced_existing: bool = False
) -> SavedInsightResponseSchema:
    return SavedInsightResponseSchema(
        id=insight.public_id,
        title=insight.title,
        summary_text=insight.summary_text,
        chart_payload=insight.chart_payload,
        created_at=insight.created_at.isoformat(),
        last_refreshed_at=insight.last_refreshed_at.isoformat(),
        replaced_existing=replaced_existing,
    )


def _serialize_policy(policy) -> SavedInsightPolicySchema:
    return SavedInsightPolicySchema(
        max_saved_insights=policy.max_saved_insights,
        current_count=policy.current_count,
        replaces_on_save=policy.replaces_on_save,
        upgrade_message=policy.upgrade_message,
    )


@router.get(
    "analytics/saved-insights",
    response={200: SavedInsightListResponseSchema, 401: ErrorResponseSchema},
)
def list_saved_insights(request):
    service = SavedInsightService()
    insights = service.list_for_user(request.user)
    return SavedInsightListResponseSchema(
        items=[_serialize_saved_insight(insight) for insight in insights],
        policy=_serialize_policy(service.get_policy_for_user(request.user)),
    )


@router.post(
    "analytics/saved-insights",
    response={
        201: SavedInsightResponseSchema,
        401: ErrorResponseSchema,
        422: ErrorResponseSchema,
        404: ErrorResponseSchema,
    },
)
def create_saved_insight(request, payload: SavedInsightRequestSchema):
    try:
        result = SavedInsightService().save_from_message(
            user=request.user,
            assistant_message_id=payload.assistant_message_id,
            block_index=payload.block_index,
        )
    except SavedInsightNotFoundError as exc:
        return 404, ErrorResponseSchema(detail=str(exc))
    except SavedInsightValidationError as exc:
        return 422, ErrorResponseSchema(detail=str(exc))

    return 201, _serialize_saved_insight(
        result.insight,
        replaced_existing=result.replaced_existing,
    )


@router.post(
    "analytics/saved-insights/{insight_id}/refresh",
    response={
        200: SavedInsightResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
        422: ErrorResponseSchema,
    },
)
def refresh_saved_insight(request, insight_id: str):
    try:
        insight = SavedInsightService().refresh(user=request.user, public_id=insight_id)
    except SavedInsightNotFoundError as exc:
        return 404, ErrorResponseSchema(detail=str(exc))
    except SavedInsightValidationError as exc:
        return 422, ErrorResponseSchema(detail=str(exc))

    return _serialize_saved_insight(insight)


@router.delete(
    "analytics/saved-insights/{insight_id}",
    response={
        200: DeleteSavedInsightResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
    },
)
def delete_saved_insight(request, insight_id: str):
    deleted = SavedInsightService().delete(user=request.user, public_id=insight_id)
    if not deleted:
        return 404, ErrorResponseSchema(detail="Saved insight not found.")

    return DeleteSavedInsightResponseSchema(success=True)
