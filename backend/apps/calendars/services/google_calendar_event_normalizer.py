from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import is_naive, make_aware

from apps.calendars.services.google_calendar_payloads import CalendarEventPayload


def _parse_google_datetime(raw_value: str, timezone_name: str) -> datetime:
    try:
        event_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        event_timezone = ZoneInfo("UTC")

    parsed_datetime = parse_datetime(raw_value)
    if parsed_datetime is not None:
        if is_naive(parsed_datetime):
            return make_aware(parsed_datetime, event_timezone)
        return parsed_datetime

    parsed_date = parse_date(raw_value)
    if parsed_date is None:
        raise ValueError("Unsupported Google event date format")

    return make_aware(datetime.combine(parsed_date, time.min), event_timezone)


def normalize_google_event(payload: dict) -> CalendarEventPayload:
    """Normalize a Google Calendar event resource into our internal CalendarEventPayload."""
    start_payload = payload.get("start", {})
    end_payload = payload.get("end", {})
    is_all_day = "date" in start_payload
    timezone_name = start_payload.get("timeZone") or end_payload.get("timeZone") or "UTC"

    start_raw = start_payload.get("dateTime") or start_payload.get("date")
    end_raw = end_payload.get("dateTime") or end_payload.get("date")
    if not start_raw or not end_raw:
        raise ValueError("Google event payload is missing a start or end value")

    return CalendarEventPayload(
        google_event_id=payload["id"][:255],
        title=(payload.get("summary") or "Untitled event")[:255],
        description=payload.get("description") or "",
        start_time=_parse_google_datetime(start_raw, timezone_name),
        end_time=_parse_google_datetime(end_raw, timezone_name),
        timezone=timezone_name,
        location=(payload.get("location") or "")[:255],
        status=payload.get("status") or "",
        attendees=payload.get("attendees") or [],
        organizer_email=(payload.get("organizer") or {}).get("email") or "",
        is_all_day=is_all_day,
    )
