from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GoogleCalendarDescriptor:
    """Minimal primary calendar metadata returned from Google."""

    google_calendar_id: str
    name: str
    is_primary: bool
    color: str = ""
    timezone: str = ""


@dataclass(frozen=True)
class CalendarEventPayload:
    """Normalized event shape used by our sync/mutation services."""

    google_event_id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    timezone: str
    location: str
    status: str
    attendees: list[dict]
    organizer_email: str
    is_all_day: bool
