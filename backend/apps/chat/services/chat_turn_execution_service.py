from __future__ import annotations

import logging

from apps.chat.models.chat_turn import ChatTurn, ChatTurnResultKind, ChatTurnScopeDecision
from apps.chat.services.chat_action_proposal_service import ChatActionProposalService
from apps.chat.services.chat_assistant_turn_service import ChatAssistantTurnService
from apps.chat.services.chat_execution_mode_profile_service import ChatExecutionModeProfileService
from apps.chat.services.chat_message_service import ChatMessageService
from apps.chat.services.chat_prompt_builder import ChatPromptBuilder
from apps.chat.services.chat_turn_service import ChatTurnService
from apps.core.exceptions import AppConfigurationError
from apps.core_agent.services.game_loop_service import GameLoopExceededMaxIterationsError

logger = logging.getLogger(__name__)


class ChatTurnExecutionService:
    prompt_version = ChatPromptBuilder.prompt_version
    capability_version = "release6-approval-gated"
    policy_version = "release6-scheduling-proposal-first"

    def __init__(
        self,
        *,
        turn_service: ChatTurnService | None = None,
        message_service: ChatMessageService | None = None,
        assistant_turn_service: ChatAssistantTurnService | None = None,
        action_proposal_service: ChatActionProposalService | None = None,
    ) -> None:
        """Execute a queued chat turn end-to-end and persist the assistant response + traces."""
        self.turn_service = turn_service or ChatTurnService()
        self.message_service = message_service or ChatMessageService()
        self.assistant_turn_service = assistant_turn_service or ChatAssistantTurnService()
        self.action_proposal_service = action_proposal_service or ChatActionProposalService()

    def process_turn(self, *, turn: ChatTurn) -> ChatTurn:
        """Run provider loop for a turn, store assistant message, and mark the turn completed/failed."""
        if turn.assistant_message_id and turn.status == "completed":
            return turn

        self.turn_service.mark_running(turn)
        self.turn_service.append_trace_event(
            turn,
            event_type="turn_received",
            summary="Turn dequeued for processing.",
            data={"user_message_id": turn.user_message_id},
        )

        user_prompt = self.message_service.render_text_content(turn.user_message)
        try:
            result = self.assistant_turn_service.generate_response(
                session=turn.session,
                user_prompt=user_prompt,
            )
        except AppConfigurationError as exc:
            logger.exception(
                "chat.turn.execution.configuration_error turn_id=%s correlation_id=%s",
                turn.id,
                turn.correlation_id,
            )
            return self._fail_turn(
                turn=turn, user_prompt=user_prompt, failure_reason="configuration_error", exc=exc
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "chat.turn.execution.failed turn_id=%s correlation_id=%s",
                turn.id,
                turn.correlation_id,
            )
            if isinstance(exc, GameLoopExceededMaxIterationsError):
                provider_name = "openai"
                provider_model = getattr(
                    self.assistant_turn_service.provider, "model_id", "unknown"
                )
                turn.provider_metadata = {
                    "raw_content": (
                        exc.loop_events[-1].get("raw_content") if exc.loop_events else None
                    ),
                    "loop_events": exc.loop_events,
                    "provider_name": provider_name,
                    "provider_model": provider_model,
                    "tool_calls": [
                        {
                            "tool_name": tool.tool_name,
                            "tool_args": dict(tool.tool_args),
                            "result": tool.result,
                        }
                        for tool in exc.tool_calls
                    ],
                }
                turn.save(update_fields=["provider_metadata"])
                self._append_loop_events(
                    turn=turn,
                    loop_events=exc.loop_events,
                    provider_name=provider_name,
                    provider_model=provider_model,
                )
            return self._fail_turn(
                turn=turn, user_prompt=user_prompt, failure_reason="provider_error", exc=exc
            )

        self.turn_service.append_trace_event(
            turn,
            event_type="provider_returned",
            summary="Provider returned a response.",
            data={
                "result_kind": result.kind,
                "tool_call_count": len(result.tool_calls),
            },
        )
        self._append_loop_events(
            turn=turn,
            loop_events=result.loop_events,
            provider_name="openai",
            provider_model=getattr(self.assistant_turn_service.provider, "model_id", "unknown"),
        )

        if turn.assistant_message_id:
            return turn

        assistant_message = self.message_service.create_assistant_message(
            turn.session,
            content_blocks=self.assistant_turn_service.build_content_blocks(result),
            tool_calls=result.tool_calls,
        )
        self.action_proposal_service.persist_from_message(
            session=turn.session,
            turn=turn,
            assistant_message=assistant_message,
        )
        eval_snapshot = self._build_eval_snapshot(
            turn=turn,
            user_prompt=user_prompt,
            result_kind=result.kind,
            assistant_text=result.text,
            used_tools=[tool.tool_name for tool in result.tool_calls],
            tool_outputs=[tool.result for tool in result.tool_calls if tool.result is not None],
            fallback_reason=None,
            provider_name="openai",
            provider_model=getattr(self.assistant_turn_service.provider, "model_id", "unknown"),
            raw_content=result.raw_content,
            loop_events=result.loop_events,
        )
        self.turn_service.mark_completed(
            turn,
            assistant_message=assistant_message,
            result_kind=result.kind,
            scope_decision=self._legacy_scope_decision(result.kind),
            provider_metadata={
                "raw_content": result.raw_content,
                "loop_events": result.loop_events,
            },
            eval_snapshot=eval_snapshot,
        )
        self.turn_service.append_trace_event(
            turn,
            event_type="turn_completed",
            summary="Turn completed with assistant response.",
            data={"assistant_message_id": assistant_message.id, "result_kind": result.kind},
        )
        return turn

    def _fail_turn(
        self, *, turn: ChatTurn, user_prompt: str, failure_reason: str, exc: Exception
    ) -> ChatTurn:
        assistant_message = turn.assistant_message
        if assistant_message is None:
            assistant_message = self.message_service.create_assistant_message(
                turn.session,
                content_blocks=[
                    {
                        "type": "text",
                        "text": "I couldn’t respond just now. Please try again.",
                    }
                ],
            )
        provider_metadata = turn.provider_metadata or {}
        failure_tool_calls = provider_metadata.get("tool_calls", [])
        provider_name = str(provider_metadata.get("provider_name") or "openai")
        provider_model = str(
            provider_metadata.get("provider_model")
            or getattr(self.assistant_turn_service.provider, "model_id", "unknown")
        )
        eval_snapshot = self._build_eval_snapshot(
            turn=turn,
            user_prompt=user_prompt,
            result_kind=ChatTurnResultKind.ERROR,
            assistant_text="I couldn’t respond just now. Please try again.",
            used_tools=[tool_call["tool_name"] for tool_call in failure_tool_calls],
            tool_outputs=[
                tool_call["result"]
                for tool_call in failure_tool_calls
                if tool_call.get("result") is not None
            ],
            fallback_reason=failure_reason,
            provider_name=provider_name,
            provider_model=provider_model,
            raw_content=provider_metadata.get("raw_content"),
            loop_events=provider_metadata.get("loop_events", []),
        )
        self.turn_service.mark_failed(
            turn, failure_reason=failure_reason, eval_snapshot=eval_snapshot
        )
        turn.assistant_message = assistant_message
        turn.save(update_fields=["assistant_message"])
        self.turn_service.append_trace_event(
            turn,
            event_type="turn_failed",
            summary="Turn failed and fallback error message was stored.",
            data={"failure_reason": failure_reason, "error": str(exc)},
        )
        return turn

    def _append_loop_events(
        self,
        *,
        turn: ChatTurn,
        loop_events: list[dict],
        provider_name: str,
        provider_model: str,
    ) -> None:
        for event in loop_events:
            if event["type"] == "loop_step_completed":
                self.turn_service.append_trace_event(
                    turn,
                    event_type="provider_step_completed",
                    summary="Provider completed a loop step.",
                    data={
                        "iteration": event["iteration"],
                        "decision": event["decision"],
                        "decision_reason": event.get("decision_reason", ""),
                        "tool_name": event["tool_name"],
                        "tool_args": event["tool_args"],
                        "kind": event["kind"],
                        "text": event["text"],
                        "provider_name": provider_name,
                        "provider_model": provider_model,
                    },
                )
                continue

            if event["type"] == "tool_executed":
                self.turn_service.append_trace_event(
                    turn,
                    event_type="tool_executed",
                    summary="Loop executed a tool call.",
                    data={
                        "iteration": event["iteration"],
                        "tool_name": event["tool_name"],
                        "tool_args": event["tool_args"],
                        "result": event["result"],
                        "provider_name": provider_name,
                        "provider_model": provider_model,
                    },
                )

    def _legacy_scope_decision(self, result_kind: str) -> str:
        # This field is retained temporarily for API/model compatibility while
        # scope classification moves out of the hardcoded pre-model path.
        if result_kind == ChatTurnResultKind.CLARIFICATION:
            return ChatTurnScopeDecision.AMBIGUOUS
        return ChatTurnScopeDecision.IN_SCOPE

    def _build_eval_snapshot(
        self,
        *,
        turn: ChatTurn,
        user_prompt: str,
        result_kind: str,
        assistant_text: str,
        used_tools: list[str],
        tool_outputs: list[str],
        fallback_reason: str | None,
        provider_name: str,
        provider_model: str,
        raw_content: str | None,
        loop_events: list[dict],
    ) -> dict:
        history_snapshot = self.message_service.serialize_history(turn.session)
        capabilities = self.assistant_turn_service.capability_service.get_release_capabilities()
        execution_mode_profile_service = getattr(
            self.assistant_turn_service,
            "execution_mode_profile_service",
            ChatExecutionModeProfileService(),
        )
        execution_profile = execution_mode_profile_service.get_profile(turn.session.user)
        tools = self.assistant_turn_service.tool_registry_service.build_tools(
            user=turn.session.user,
            profile=execution_profile,
        )
        return {
            "user_prompt": user_prompt,
            "history_snapshot": history_snapshot,
            "scope_decision": turn.scope_decision,
            "allowed_tools": [tool.name for tool in tools],
            "used_tools": used_tools,
            "tool_outputs": tool_outputs,
            "assistant_kind": result_kind,
            "assistant_text": assistant_text,
            "fallback_reason": fallback_reason,
            "provider_name": provider_name,
            "provider_model": provider_model,
            "provider_raw_content": raw_content,
            "loop_events": loop_events,
            "prompt_version": self.prompt_version,
            "capability_version": self.capability_version,
            "policy_version": self.policy_version,
            "enabled_capabilities": [
                capability.name for capability in capabilities if capability.enabled
            ],
        }
