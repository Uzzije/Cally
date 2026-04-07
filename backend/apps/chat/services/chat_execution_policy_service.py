from __future__ import annotations

from dataclasses import dataclass

from apps.chat.models.action_proposal import ActionProposal
from apps.preferences.models.user_preferences import ExecutionMode
from apps.preferences.services.preference_query_service import PreferenceQueryService


@dataclass(frozen=True)
class ExecutionPolicyDecision:
    allowed: bool
    reason: str | None = None


class ChatExecutionPolicyService:
    def __init__(
        self,
        *,
        preference_query_service: PreferenceQueryService | None = None,
    ) -> None:
        self.preference_query_service = preference_query_service or PreferenceQueryService()

    def evaluate(self, *, user, proposal: ActionProposal) -> ExecutionPolicyDecision:
        preferences = self.preference_query_service.get_for_user(user)

        if preferences.execution_mode == ExecutionMode.DRAFT_ONLY:
            return ExecutionPolicyDecision(
                allowed=False,
                reason="Draft-only mode keeps this proposal review-only. Switch to Confirm in Settings to execute it.",
            )

        if proposal.action_type != "create_event":
            return ExecutionPolicyDecision(
                allowed=False,
                reason="This proposal type is not executable in the current release.",
            )

        return ExecutionPolicyDecision(allowed=True)
