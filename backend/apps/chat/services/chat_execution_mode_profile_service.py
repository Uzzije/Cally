from __future__ import annotations

from dataclasses import dataclass

from apps.core.types import AuthenticatedUser
from apps.preferences.models.user_preferences import ExecutionMode
from apps.preferences.services.preference_query_service import PreferenceQueryService


@dataclass(frozen=True)
class ChatExecutionModeProfile:
    execution_mode: str
    workspace_mode: str
    mutation_mode: str
    mutation_prompt_label: str
    action_card_status: str
    allow_direct_mutation_tools: bool
    grounded_mutation_finish_instruction: str

    def to_session_dict(self) -> dict[str, str | bool]:
        return {
            "execution_mode": self.execution_mode,
            "workspace_mode": self.workspace_mode,
            "mutation_mode": self.mutation_mode,
            "mutation_prompt_label": self.mutation_prompt_label,
            "action_card_status": self.action_card_status,
            "allow_direct_mutation_tools": self.allow_direct_mutation_tools,
            "grounded_mutation_finish_instruction": self.grounded_mutation_finish_instruction,
        }


class ChatExecutionModeProfileService:
    def __init__(
        self,
        *,
        preference_query_service: PreferenceQueryService | None = None,
    ) -> None:
        self.preference_query_service = preference_query_service or PreferenceQueryService()

    def get_profile(self, user: AuthenticatedUser) -> ChatExecutionModeProfile:
        preferences = self.preference_query_service.get_for_user(user)
        return self.from_execution_mode(execution_mode=preferences.execution_mode)

    def from_execution_mode(self, *, execution_mode: str) -> ChatExecutionModeProfile:
        profiles = {
            ExecutionMode.DRAFT_ONLY: ChatExecutionModeProfile(
                execution_mode=ExecutionMode.DRAFT_ONLY,
                workspace_mode="draft_only",
                mutation_mode="action_card",
                mutation_prompt_label="review-only proposal",
                action_card_status="pending",
                allow_direct_mutation_tools=False,
                grounded_mutation_finish_instruction=(
                    "When a calendar change is sufficiently grounded, finish with one "
                    "reviewable action_card instead of asking for optional extras."
                ),
            ),
            ExecutionMode.CONFIRM: ChatExecutionModeProfile(
                execution_mode=ExecutionMode.CONFIRM,
                workspace_mode="confirm_before_execute",
                mutation_mode="action_card",
                mutation_prompt_label="approval-gated proposal",
                action_card_status="pending",
                allow_direct_mutation_tools=False,
                grounded_mutation_finish_instruction=(
                    "When a calendar change is sufficiently grounded, finish with one "
                    "approval-gated action_card instead of asking for optional extras."
                ),
            ),
        }
        if execution_mode == ExecutionMode.CONFIRM:
            return profiles[ExecutionMode.CONFIRM]
        return profiles[ExecutionMode.DRAFT_ONLY]
