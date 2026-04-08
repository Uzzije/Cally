from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypedDict
from zoneinfo import ZoneInfo

from django.db.models import QuerySet
from django.utils import timezone

from apps.analytics.constants import SUPPORTED_ANALYTICS_QUERY_TYPES
from apps.calendars.models.event import Event
from apps.core.types import AuthenticatedUser
from apps.calendars.services.calendar_query_service import CalendarQueryService


class AnalyticsQueryServiceError(ValueError):
    pass


@dataclass(frozen=True)
class AnalyticsQueryResult:
    summary_text: str
    chart_block: dict


class ChartDataPoint(TypedDict):
    label: str
    value: float


class AnalyticsQueryService:
    supported_query_types = SUPPORTED_ANALYTICS_QUERY_TYPES

    def __init__(self, *, calendar_query_service: CalendarQueryService | None = None) -> None:
        """Run supported analytics queries over synced calendar events."""
        self.calendar_query_service = calendar_query_service or CalendarQueryService()

    def run(self, *, user: AuthenticatedUser, query_type: str) -> AnalyticsQueryResult:
        """Dispatch a supported analytics query and return summary text plus a chart payload."""
        if query_type not in self.supported_query_types:
            raise AnalyticsQueryServiceError(f"Unsupported analytics query_type: {query_type}.")

        if query_type == "meeting_hours_by_weekday_this_week":
            return self._meeting_hours_by_weekday_this_week(user)

        return self._busiest_day_last_14_days(user)

    def _meeting_hours_by_weekday_this_week(self, user: AuthenticatedUser) -> AnalyticsQueryResult:
        tz = ZoneInfo(self.calendar_query_service.get_default_timezone(user))
        now_local = timezone.now().astimezone(tz)
        start_of_week = (now_local - timedelta(days=now_local.weekday())).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        end_of_week = start_of_week + timedelta(days=7)

        weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        totals = {label: 0.0 for label in weekday_labels}

        for event in self._events_for_range(user, start=start_of_week, end=end_of_week):
            local_start = event.start_time.astimezone(tz)
            local_end = event.end_time.astimezone(tz)
            label = weekday_labels[local_start.weekday()]
            totals[label] += max((local_end - local_start).total_seconds() / 3600, 0)

        data: list[ChartDataPoint] = [
            {"label": label, "value": round(totals[label], 1)} for label in weekday_labels
        ]
        peak_day = max(data, key=lambda item: item["value"])
        summary_text = (
            f"You have {sum(item['value'] for item in data):.1f} hours of meetings this week so far. "
            f"{peak_day['label']} is the busiest day at {peak_day['value']:.1f} hours."
        )
        return AnalyticsQueryResult(
            summary_text=summary_text,
            chart_block={
                "type": "chart",
                "chart_type": "bar",
                "title": "Meeting hours this week",
                "subtitle": "Based on synced events grouped by weekday.",
                "data": data,
                "save_enabled": True,
            },
        )

    def _busiest_day_last_14_days(self, user: AuthenticatedUser) -> AnalyticsQueryResult:
        tz = ZoneInfo(self.calendar_query_service.get_default_timezone(user))
        now_local = timezone.now().astimezone(tz)
        start = (now_local - timedelta(days=13)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now_local + timedelta(days=1)

        totals: dict[str, int] = {}
        for event in self._events_for_range(user, start=start, end=end):
            local_start = event.start_time.astimezone(tz)
            label = f"{local_start.strftime('%b')} {local_start.day}"
            totals[label] = totals.get(label, 0) + 1

        if not totals:
            data: list[ChartDataPoint] = [
                {"label": f"{start.strftime('%b')} {start.day}", "value": 0}
            ]
            summary_text = "I couldn't find any meetings in the last 14 days."
        else:
            data = [
                {"label": label, "value": float(count)} for label, count in sorted(totals.items())
            ]
            peak_day = max(data, key=lambda item: item["value"])
            summary_text = (
                f"Your busiest day in the last 14 days was {peak_day['label']} "
                f"with {peak_day['value']} meetings."
            )

        return AnalyticsQueryResult(
            summary_text=summary_text,
            chart_block={
                "type": "chart",
                "chart_type": "bar",
                "title": "Busiest days in the last 14 days",
                "subtitle": "Count of synced meetings by day.",
                "data": data,
                "save_enabled": True,
            },
        )

    def _events_for_range(
        self, user: AuthenticatedUser, *, start: datetime, end: datetime
    ) -> QuerySet[Event]:
        return Event.objects.select_related("calendar").filter(
            calendar__user=user,
            start_time__lt=end,
            end_time__gt=start,
        )
