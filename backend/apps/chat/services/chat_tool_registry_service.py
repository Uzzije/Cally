from __future__ import annotations

import json
from datetime import datetime

from apps.calendars.services.calendar_query_service import CalendarQueryService
from apps.core_agent.models.tool_definition import ToolDefinition


class ChatToolRegistryService:
    def __init__(self, *, query_service: CalendarQueryService | None = None) -> None:
        self.query_service = query_service or CalendarQueryService()

    def build_tools(self, *, user) -> list[ToolDefinition]:
        def get_events(*, start: str, end: str) -> str:
            """
            Get calendar events for the authenticated user between ISO datetime start and end.
            """

            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            events = self.query_service.get_events_for_range(user, start=start_dt, end=end_dt)
            return json.dumps([self._serialize_event(event) for event in events])

        def search_events(*, query: str, limit: int = 5) -> str:
            """
            Search the authenticated user's calendar events by title, description, location, or organizer.
            """

            events = self.query_service.search_events(user, query=query, limit=limit)
            return json.dumps([self._serialize_event(event) for event in events])

        return [
            ToolDefinition(
                name="get_events",
                description="Get calendar events in an ISO datetime range.",
                handler=get_events,
            ),
            ToolDefinition(
                name="search_events",
                description="Search calendar events by keyword.",
                handler=search_events,
            ),
        ]

    def _serialize_event(self, event) -> dict:
        return {
            "id": event.id,
            "google_event_id": event.google_event_id,
            "title": event.title,
            "description": event.description,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "timezone": event.timezone,
            "location": event.location,
            "status": event.status,
            "organizer_email": event.organizer_email,
            "is_all_day": event.is_all_day,
        }

