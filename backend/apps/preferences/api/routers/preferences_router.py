import logging

from ninja import Router

from apps.core.api.auth import session_auth
from apps.preferences.api.schemas.error_response_schema import ErrorResponseSchema
from apps.preferences.api.schemas.temporary_blocked_time_schema import TemporaryBlockedTimeSchema
from apps.preferences.api.schemas.temporary_blocked_time_request_schema import (
    TemporaryBlockedTimeBulkCreateRequestSchema,
)
from apps.preferences.api.schemas.temporary_blocked_times_response_schema import (
    TemporaryBlockedTimesResponseSchema,
)
from apps.preferences.api.schemas.user_preferences_request_schema import (
    UserPreferencesRequestSchema,
)
from apps.preferences.api.schemas.user_preferences_response_schema import (
    UserPreferencesResponseSchema,
)
from apps.preferences.services.preference_query_service import PreferenceQueryService
from apps.preferences.services.preference_update_service import PreferenceUpdateService
from apps.preferences.services.preferences_validation_error import PreferencesValidationError
from apps.preferences.services.temporary_blocked_time_service import (
    TemporaryBlockedTimeCreateRequest,
    TemporaryBlockedTimeNotFoundError,
    TemporaryBlockedTimeService,
    TemporaryBlockedTimeValidationError,
)
from apps.preferences.services.temporary_blocked_time_trigger_service import (
    TemporaryBlockedTimeTriggerService,
)

router = Router(tags=["settings"], auth=session_auth)
logger = logging.getLogger(__name__)


def _serialize_preferences(preferences):
    return UserPreferencesResponseSchema(
        execution_mode=preferences.execution_mode,
        display_timezone=preferences.display_timezone or None,
        blocked_times=preferences.blocked_times,
    )


def _serialize_temporary_blocked_times(entries):
    service = TemporaryBlockedTimeService()
    return TemporaryBlockedTimesResponseSchema(
        entries=[TemporaryBlockedTimeSchema(**service.serialize(entry)) for entry in entries]
    )


@router.get(
    "preferences",
    response={200: UserPreferencesResponseSchema, 401: ErrorResponseSchema},
)
def get_preferences(request):
    preferences = PreferenceQueryService().get_for_user(request.user)
    return _serialize_preferences(preferences)


@router.put(
    "preferences",
    response={
        200: UserPreferencesResponseSchema,
        401: ErrorResponseSchema,
        422: ErrorResponseSchema,
    },
)
def update_preferences(request, payload: UserPreferencesRequestSchema):
    try:
        preferences = PreferenceUpdateService().update_for_user(
            request.user,
            execution_mode=payload.execution_mode,
            display_timezone=payload.display_timezone,
            blocked_times=[item.model_dump() for item in payload.blocked_times],
        )
    except PreferencesValidationError as exc:
        return 422, ErrorResponseSchema(detail=exc.detail, errors=exc.errors)

    return _serialize_preferences(preferences)


@router.get(
    "temp-blocked-times",
    response={200: TemporaryBlockedTimesResponseSchema, 401: ErrorResponseSchema},
)
def get_temporary_blocked_times(request):
    entries = PreferenceQueryService().get_active_temporary_blocked_times(request.user)
    return _serialize_temporary_blocked_times(entries)


@router.post(
    "temp-blocked-times",
    response={
        200: TemporaryBlockedTimesResponseSchema,
        401: ErrorResponseSchema,
        422: ErrorResponseSchema,
    },
)
def create_temporary_blocked_times(request, payload: TemporaryBlockedTimeBulkCreateRequestSchema):
    service = TemporaryBlockedTimeService()
    try:
        entries = service.create_many_for_user(
            request.user,
            requests=[
                TemporaryBlockedTimeCreateRequest(
                    label=entry.label,
                    date=entry.date,
                    start=entry.start,
                    end=entry.end,
                    timezone=payload.timezone,
                    source=entry.source,
                )
                for entry in payload.entries
            ],
        )
    except TemporaryBlockedTimeValidationError as exc:
        return 422, ErrorResponseSchema(detail=exc.detail, errors=exc.errors)

    try:
        TemporaryBlockedTimeTriggerService().request_expiry_cleanup(
            user_id=request.user.id,
            public_ids=[entry.public_id for entry in entries],
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "preferences.temporary_blocked_times.cleanup_request_failed user_id=%s",
            request.user.id,
        )
    return _serialize_temporary_blocked_times(entries)


@router.delete(
    "temp-blocked-times",
    response={200: TemporaryBlockedTimesResponseSchema, 401: ErrorResponseSchema},
)
def clear_temporary_blocked_times(request):
    TemporaryBlockedTimeService().clear_for_user(request.user)
    return TemporaryBlockedTimesResponseSchema(entries=[])


@router.delete(
    "temp-blocked-times/{entry_id}",
    response={
        200: TemporaryBlockedTimesResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
    },
)
def delete_temporary_blocked_time(request, entry_id: str):
    service = TemporaryBlockedTimeService()
    try:
        service.delete_for_user(request.user, public_id=entry_id)
    except TemporaryBlockedTimeNotFoundError as exc:
        return 404, ErrorResponseSchema(detail=str(exc))

    entries = PreferenceQueryService().get_active_temporary_blocked_times(request.user)
    return _serialize_temporary_blocked_times(entries)
