from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from apps.calendars.services.google_calendar_client import (
    GoogleCalendarClient,
    GoogleCalendarClientError,
)
from apps.core.types import AuthenticatedUser

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttendeeAvailabilityResult:
    busy_ranges_by_attendee: dict[str, list[tuple[datetime, datetime]]]
    degraded: bool


class CalendarAttendeeAvailabilityService:
    def __init__(
        self,
        *,
        google_calendar_client: GoogleCalendarClient | None = None,
    ) -> None:
        self.google_calendar_client = google_calendar_client or GoogleCalendarClient()

    def lookup_attendee_busy_ranges(
        self,
        *,
        user: AuthenticatedUser,
        attendee_emails: list[str],
        start: datetime,
        end: datetime,
    ) -> AttendeeAvailabilityResult:
        normalized_emails = sorted(
            {
                email.strip().lower()
                for email in attendee_emails
                if isinstance(email, str) and "@" in email and email.strip()
            }
        )
        if not normalized_emails:
            return AttendeeAvailabilityResult(
                busy_ranges_by_attendee={},
                degraded=False,
            )

        try:
            busy_ranges = self.google_calendar_client.get_free_busy(
                user,
                attendee_emails=normalized_emails,
                time_min=start,
                time_max=end,
            )
        except GoogleCalendarClientError as exc:
            logger.warning(
                "calendar.attendee_availability.degraded user_id=%s attendees=%s reason=%s",
                user.id,
                ",".join(normalized_emails),
                str(exc),
            )
            return AttendeeAvailabilityResult(
                busy_ranges_by_attendee={},
                degraded=True,
            )

        logger.info(
            "calendar.attendee_availability.loaded user_id=%s attendee_count=%s",
            user.id,
            len(normalized_emails),
        )
        return AttendeeAvailabilityResult(
            busy_ranges_by_attendee=busy_ranges,
            degraded=False,
        )
