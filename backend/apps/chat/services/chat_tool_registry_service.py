from __future__ import annotations

import json
from datetime import datetime

from apps.analytics.services.analytics_query_service import AnalyticsQueryService
from apps.calendars.services.calendar_query_service import CalendarQueryService
from apps.calendars.services.calendar_event_mutation_service import (
    CalendarEventMutationRequest,
    CalendarEventMutationService,
)
from apps.core_agent.decorators import agent_tool
from apps.core_agent.models.tool_definition import ToolDefinition
from apps.chat.services.chat_email_draft_block_service import ChatEmailDraftBlockService
from apps.chat.services.chat_execution_mode_profile_service import ChatExecutionModeProfile
from apps.preferences.services.preference_query_service import PreferenceQueryService


class ChatToolRegistryService:
    def __init__(
        self,
        *,
        analytics_query_service: AnalyticsQueryService | None = None,
        query_service: CalendarQueryService | None = None,
        calendar_event_mutation_service: CalendarEventMutationService | None = None,
        preference_query_service: PreferenceQueryService | None = None,
        email_draft_block_service: ChatEmailDraftBlockService | None = None,
    ) -> None:
        self.analytics_query_service = analytics_query_service or AnalyticsQueryService()
        self.query_service = query_service or CalendarQueryService()
        self.calendar_event_mutation_service = (
            calendar_event_mutation_service or CalendarEventMutationService()
        )
        self.preference_query_service = preference_query_service or PreferenceQueryService()
        self.email_draft_block_service = email_draft_block_service or ChatEmailDraftBlockService()

    def build_tools(self, *, user, profile: ChatExecutionModeProfile) -> list[ToolDefinition]:
        @agent_tool(name="get_events", description="Get calendar events in an ISO datetime range.")
        def get_events(*, start: str, end: str) -> str:
            """
            Get calendar events for the authenticated user between ISO datetime start and end.
            """

            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            events = self.query_service.get_events_for_range(user, start=start_dt, end=end_dt)
            return json.dumps([self._serialize_event(event) for event in events])

        @agent_tool(name="search_events", description="Search calendar events by keyword.")
        def search_events(*, query: str, limit: int = 5) -> str:
            """
            Search the authenticated user's calendar events by title, description, location, or organizer.
            """

            events = self.query_service.search_events(user, query=query, limit=limit)
            return json.dumps([self._serialize_event(event) for event in events])

        @agent_tool(
            name="get_preferences", description="Get saved planning preferences and blocked times."
        )
        def get_preferences() -> str:
            """
            Get the authenticated user's saved planning preferences and blocked times.
            """

            preferences = self.preference_query_service.get_for_user(user)
            return json.dumps(
                {
                    "execution_mode": preferences.execution_mode,
                    "display_timezone": preferences.display_timezone or None,
                    "blocked_times": preferences.blocked_times,
                    "temp_blocked_times": [
                        {
                            "id": blocked_time.public_id,
                            "label": blocked_time.label,
                            "start_time": blocked_time.start_time.isoformat(),
                            "end_time": blocked_time.end_time.isoformat(),
                            "timezone": blocked_time.timezone,
                            "source": blocked_time.source,
                            "expires_at": blocked_time.expires_at.isoformat(),
                        }
                        for blocked_time in self.preference_query_service.get_active_temporary_blocked_times(
                            user
                        )
                    ],
                }
            )

        @agent_tool(
            name="query_analytics",
            description=(
                "Run one approved read-only analytics query over the user's synced calendar data. "
                "Supported query_type values: meeting_hours_by_weekday_this_week, busiest_day_last_14_days."
            ),
        )
        def query_analytics(*, query_type: str) -> str:
            result = self.analytics_query_service.run(user=user, query_type=query_type)
            return json.dumps(
                {
                    "summary_text": result.summary_text,
                    "chart_block": result.chart_block,
                }
            )

        @agent_tool(
            name="build_email_draft",
            description="Build a grounded email_draft block for a scheduling-related draft preview.",
        )
        def build_email_draft(
            *,
            to: list[str],
            draft_markdown: str,
            cc: list[str] | None = None,
            status_detail: str | None = None,
        ) -> str:
            """
            Build a validated draft preview block from markdown with a Subject: line and body.
            """

            return json.dumps(
                self.email_draft_block_service.build_block_from_markdown(
                    to=to,
                    cc=cc or [],
                    draft_markdown=draft_markdown,
                    status_detail=status_detail,
                )
            )

        tools = [
            ToolDefinition.from_callable(get_events),
            ToolDefinition.from_callable(search_events),
            ToolDefinition.from_callable(get_preferences),
            ToolDefinition.from_callable(query_analytics),
            ToolDefinition.from_callable(build_email_draft),
        ]

        if profile.allow_direct_mutation_tools:

            @agent_tool(
                name="create_event", description="Create an event on the user's primary calendar."
            )
            def create_event(
                *,
                title: str,
                start_time: str,
                end_time: str,
                timezone: str,
                attendee_emails: list[str] | None = None,
            ) -> str:
                result = self.calendar_event_mutation_service.create_primary_calendar_event(
                    user,
                    request=CalendarEventMutationRequest(
                        title=title,
                        start_time=start_time,
                        end_time=end_time,
                        timezone=timezone,
                        attendee_emails=attendee_emails or [],
                    ),
                )
                return json.dumps(
                    {
                        "event_id": result.event_id,
                        "google_event_id": result.google_event_id,
                    }
                )

            tools.append(ToolDefinition.from_callable(create_event))

        return tools

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
            "attendees": event.attendees,
            "organizer_email": event.organizer_email,
            "is_all_day": event.is_all_day,
        }
