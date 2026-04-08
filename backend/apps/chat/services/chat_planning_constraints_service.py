from __future__ import annotations

from dataclasses import dataclass, field

from apps.core.types import AuthenticatedUser
from apps.preferences.services.preference_query_service import PreferenceQueryService


@dataclass(frozen=True)
class PlanningConstraints:
    execution_mode: str = "draft_only"
    display_timezone: str | None = None
    blocked_times: list[dict] = field(default_factory=list)
    temp_blocked_times: list[dict] = field(default_factory=list)


class ChatPlanningConstraintsService:
    def __init__(
        self,
        *,
        preference_query_service: PreferenceQueryService | None = None,
    ) -> None:
        """Expose preferences-derived planning constraints for agent prompts/session state."""
        self.preference_query_service = preference_query_service or PreferenceQueryService()

    def get_constraints(self, user: AuthenticatedUser) -> PlanningConstraints:
        """Return planning constraints including weekly + temporary blocked times."""
        preferences = self.preference_query_service.get_for_user(user)
        return PlanningConstraints(
            execution_mode=preferences.execution_mode,
            display_timezone=preferences.display_timezone or None,
            blocked_times=preferences.blocked_times,
            temp_blocked_times=[
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
        )
