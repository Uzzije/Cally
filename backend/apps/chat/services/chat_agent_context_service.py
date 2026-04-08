from __future__ import annotations

from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.calendars.services.calendar_query_service import CalendarQueryService
from apps.chat.models.chat_session import ChatSession
from apps.chat.services.chat_execution_mode_profile_service import ChatExecutionModeProfile
from apps.chat.services.chat_planning_constraints_service import ChatPlanningConstraintsService
from apps.core_agent.models.agent_capability import AgentCapability
from apps.core_agent.models.tool_definition import ToolDefinition


class ChatAgentContextService:
    def __init__(
        self,
        *,
        query_service: CalendarQueryService | None = None,
        planning_constraints_service: ChatPlanningConstraintsService | None = None,
    ) -> None:
        """Build the runtime session_state snapshot provided to the agent loop."""
        self.query_service = query_service or CalendarQueryService()
        self.planning_constraints_service = (
            planning_constraints_service or ChatPlanningConstraintsService()
        )

    def build_session_state(
        self,
        *,
        session: ChatSession,
        capabilities: list[AgentCapability],
        tools: list[ToolDefinition],
        execution_profile: ChatExecutionModeProfile,
    ) -> dict:
        """Assemble timezone, sync status, tools, and planning constraints into `session_state`."""
        default_timezone = self.query_service.get_default_timezone(session.user)
        now = timezone.localtime(timezone.now(), ZoneInfo(default_timezone))
        sync_status = self.query_service.get_sync_status(session.user)
        planning_constraints = self.planning_constraints_service.get_constraints(session.user)

        return {
            "workspace": {
                "product": "Cal Assistant",
                "session_id": session.id,
                "session_title": session.title,
                "mode": execution_profile.workspace_mode,
                "default_timezone": default_timezone,
                "display_timezone_preference": planning_constraints.display_timezone,
                "current_time": now.isoformat(),
                "current_date": now.date().isoformat(),
                "current_weekday": now.strftime("%A"),
            },
            "execution_profile": execution_profile.to_session_dict(),
            "capabilities": [
                {
                    "name": capability.name,
                    "description": capability.description,
                    "enabled": capability.enabled,
                }
                for capability in capabilities
            ],
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                }
                for tool in tools
            ],
            "calendar_environment": {
                "has_calendar": sync_status.has_calendar,
                "sync_state": sync_status.sync_state,
                "last_synced_at": sync_status.last_synced_at,
                "is_stale": sync_status.is_stale,
            },
            "planning_constraints": {
                "execution_mode": planning_constraints.execution_mode,
                "display_timezone": planning_constraints.display_timezone,
                "blocked_times": planning_constraints.blocked_times,
                "temp_blocked_times": planning_constraints.temp_blocked_times,
            },
        }
