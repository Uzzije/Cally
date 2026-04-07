from __future__ import annotations

from dataclasses import dataclass
import re

from apps.core_agent.models.agent_turn_result import AgentTurnResult


@dataclass(frozen=True)
class ChatScopeDecisionResult:
    scope_decision: str
    result_kind: str
    text: str
    should_invoke_provider: bool


class ChatScopePolicyService:
    greeting_pattern = re.compile(
        r"^(hi|hello|hey|good (morning|afternoon|evening))\b", re.IGNORECASE
    )

    def classify(self, user_prompt: str) -> ChatScopeDecisionResult:
        normalized = user_prompt.strip().lower()

        if self.greeting_pattern.search(normalized):
            return ChatScopeDecisionResult(
                scope_decision="greeting",
                result_kind="answer",
                text="",
                should_invoke_provider=True,
            )

        if self._is_proposal_request(normalized):
            decision = "ambiguous" if self._proposal_needs_date_context(normalized) else "in_scope"
            return ChatScopeDecisionResult(
                scope_decision=decision,
                result_kind="clarification" if decision == "ambiguous" else "answer",
                text="",
                should_invoke_provider=True,
            )

        if self._is_mutation_request(normalized):
            return ChatScopeDecisionResult(
                scope_decision="mutation_request",
                result_kind="fallback",
                text="",
                should_invoke_provider=True,
            )

        if self._is_in_scope(normalized):
            decision = "ambiguous" if self._needs_clarification(normalized) else "in_scope"
            return ChatScopeDecisionResult(
                scope_decision=decision,
                result_kind="clarification" if decision == "ambiguous" else "answer",
                text="",
                should_invoke_provider=True,
            )

        return ChatScopeDecisionResult(
            scope_decision="out_of_scope",
            result_kind="fallback",
            text="",
            should_invoke_provider=True,
        )

    def build_policy_response(self, result: ChatScopeDecisionResult) -> AgentTurnResult:
        text = result.text or self._default_text_for_scope(result.scope_decision)
        return AgentTurnResult(
            kind=result.result_kind,
            text=text,
        )

    def _is_mutation_request(self, normalized_prompt: str) -> bool:
        return any(
            verb in normalized_prompt
            for verb in (
                "schedule ",
                "create ",
                "book ",
                "move ",
                "reschedule ",
                "cancel ",
                "delete ",
                "update ",
                "send ",
                "draft ",
                "email ",
            )
        )

    def _is_in_scope(self, normalized_prompt: str) -> bool:
        return (
            any(
                term in normalized_prompt
                for term in (
                    "calendar",
                    "meeting",
                    "meetings",
                    "event",
                    "events",
                    "schedule",
                    "free",
                    "busy",
                    "tomorrow",
                    "today",
                    "week",
                    "availability",
                    "preference",
                    "preferences",
                    "setting",
                    "settings",
                    "blocked time",
                    "blocked times",
                    "execution mode",
                )
            )
            or "do i have anything" in normalized_prompt
        )

    def _needs_clarification(self, normalized_prompt: str) -> bool:
        return normalized_prompt in {"do i have anything?", "do i have anything", "anything"}

    def _default_text_for_scope(self, scope_decision: str) -> str:
        if scope_decision == "greeting":
            return (
                "Hi. I can help with calendar and workspace questions like "
                "“What does tomorrow look like?”, “When is my next meeting?”, or "
                "“Find events with design in the title.”"
            )
        if scope_decision == "mutation_request":
            return (
                "I can only make calendar changes through an approval step. For supported "
                "scheduling requests, I’ll first show a proposal card for you to review."
            )
        return (
            "I only handle calendar and workspace questions in this environment. "
            "You can ask things like “What does tomorrow look like?”, "
            "“How busy am I on Friday?”, or “Find events with Alex.”"
        )

    def _is_proposal_request(self, normalized_prompt: str) -> bool:
        proposal_terms = (
            "schedule",
            "book",
            "find time",
            "available",
            "availability",
            "free slot",
            "free slots",
        )
        return "meeting" in normalized_prompt and any(
            term in normalized_prompt for term in proposal_terms
        )

    def _proposal_needs_date_context(self, normalized_prompt: str) -> bool:
        return "today" not in normalized_prompt and "tomorrow" not in normalized_prompt
