from django.utils.dateparse import parse_datetime
from ninja import Router

from apps.calendars.api.schemas.calendar_events_response_schema import CalendarEventsResponseSchema
from apps.calendars.api.schemas.calendar_response_schema import CalendarResponseSchema
from apps.calendars.api.schemas.calendar_sync_response_schema import CalendarSyncResponseSchema
from apps.calendars.api.schemas.calendar_sync_status_response_schema import (
    CalendarSyncStatusResponseSchema,
)
from apps.calendars.api.schemas.error_response_schema import ErrorResponseSchema
from apps.calendars.api.schemas.event_response_schema import EventResponseSchema
from apps.calendars.services.calendar_query_service import CalendarQueryService
from apps.calendars.services.calendar_sync_trigger_service import CalendarSyncTriggerService


router = Router(tags=["calendar"])


def _require_authenticated_user(request):
    if request.user.is_authenticated:
        return None

    return 401, {"detail": "Authentication credentials were not provided."}


def _parse_range_value(raw_value: str):
    return parse_datetime(raw_value.replace(" ", "+"))


@router.get(
    "events",
    response={
        200: CalendarEventsResponseSchema,
        400: ErrorResponseSchema,
        401: ErrorResponseSchema,
    },
)
def get_calendar_events(request, start: str, end: str):
    auth_error = _require_authenticated_user(request)
    if auth_error:
        return auth_error

    start_dt = _parse_range_value(start)
    end_dt = _parse_range_value(end)
    if start_dt is None or end_dt is None:
        return 400, {"detail": "Invalid calendar range."}

    query_service = CalendarQueryService()
    calendar = query_service.get_primary_calendar(request.user)
    events = query_service.get_events_for_range(request.user, start=start_dt, end=end_dt)

    return CalendarEventsResponseSchema(
        calendar=(
            CalendarResponseSchema(
                id=calendar.id,
                name=calendar.name,
                is_primary=calendar.is_primary,
                last_synced_at=calendar.last_synced_at.isoformat() if calendar.last_synced_at else None,
            )
            if calendar
            else None
        ),
        events=[
            EventResponseSchema(
                id=event.id,
                google_event_id=event.google_event_id,
                title=event.title,
                description=event.description,
                start_time=event.start_time.isoformat(),
                end_time=event.end_time.isoformat(),
                timezone=event.timezone,
                location=event.location,
                status=event.status,
                attendees=event.attendees,
                organizer_email=event.organizer_email,
                is_all_day=event.is_all_day,
            )
            for event in events
        ],
    )


@router.get(
    "sync-status",
    response={200: CalendarSyncStatusResponseSchema, 401: ErrorResponseSchema},
)
def get_calendar_sync_status(request):
    auth_error = _require_authenticated_user(request)
    if auth_error:
        return auth_error

    sync_status = CalendarQueryService().get_sync_status(request.user)
    return CalendarSyncStatusResponseSchema(
        has_calendar=sync_status.has_calendar,
        sync_state=sync_status.sync_state,
        last_synced_at=sync_status.last_synced_at,
        is_stale=sync_status.is_stale,
    )


@router.post(
    "sync",
    response={200: CalendarSyncResponseSchema, 401: ErrorResponseSchema, 503: ErrorResponseSchema},
)
def sync_calendar(request):
    auth_error = _require_authenticated_user(request)
    if auth_error:
        return auth_error

    try:
        event_ids = CalendarSyncTriggerService().request_primary_calendar_sync(request.user)
    except Exception:  # noqa: BLE001
        return 503, {"detail": "Unable to enqueue calendar sync request."}

    return CalendarSyncResponseSchema(
        accepted=True,
        event_ids=event_ids,
    )
