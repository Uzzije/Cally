from __future__ import annotations

import logging

from apps.core_agent.models.agent_loop_step_request import AgentLoopStepRequest
from apps.core_agent.models.agent_loop_step_result import AgentLoopStepResult
from apps.core_agent.models.agent_turn_request import AgentTurnRequest
from apps.core_agent.models.agent_turn_result import AgentTurnResult
from apps.core_agent.models.tool_definition import ToolDefinition
from apps.core_agent.models.tool_execution_result import ToolExecutionResult
from apps.core_agent.providers.agent_provider import AgentProvider

logger = logging.getLogger(__name__)


class GameLoopExceededMaxIterationsError(RuntimeError):
    def __init__(self, *, tool_calls: list[ToolExecutionResult], loop_events: list[dict]) -> None:
        super().__init__("Game loop exceeded max iterations without finishing.")
        self.tool_calls = list(tool_calls)
        self.loop_events = list(loop_events)


class GameLoopService:
    def __init__(self, *, provider: AgentProvider, max_iterations: int = 4) -> None:
        self.provider = provider
        self.max_iterations = max_iterations

    def run(self, request: AgentTurnRequest) -> AgentTurnResult:
        tool_calls: list[ToolExecutionResult] = []
        loop_events: list[dict] = []
        tool_lookup = {tool.name: tool for tool in request.tools}

        for iteration in range(1, self.max_iterations + 1):
            step_request = AgentLoopStepRequest(
                message=request.message,
                system_prompt=request.system_prompt,
                history=list(request.history),
                tools=list(request.tools),
                tool_calls=list(tool_calls),
                session_state=dict(request.session_state),
                session_id=request.session_id,
                user_id=request.user_id,
                metadata=dict(request.metadata),
                iteration=iteration,
                max_iterations=self.max_iterations,
            )
            step_result = self.provider.run_step(step_request)
            self._validate_step_result(step_result)

            logger.info(
                "core_agent.game_loop.step_completed session_id=%s iteration=%s/%s decision=%s",
                request.session_id,
                iteration,
                self.max_iterations,
                step_result.decision,
            )
            loop_events.append(
                {
                    "type": "loop_step_completed",
                    "iteration": iteration,
                    "decision": step_result.decision,
                    "tool_name": step_result.tool_name or "",
                    "tool_args": dict(step_result.tool_args),
                    "kind": step_result.kind or "",
                    "text": step_result.text,
                    "raw_content": step_result.raw_content,
                }
            )

            if step_result.decision == "finish":
                return AgentTurnResult(
                    kind=step_result.kind or "fallback",
                    text=step_result.text,
                    content_blocks=list(step_result.content_blocks),
                    tool_calls=tool_calls,
                    loop_events=loop_events,
                    raw_content=step_result.raw_content,
                )

            tool_result = self._execute_tool(step_result=step_result, tool_lookup=tool_lookup)
            tool_calls.append(tool_result)
            loop_events.append(
                {
                    "type": "tool_executed",
                    "iteration": iteration,
                    "tool_name": tool_result.tool_name,
                    "tool_args": dict(tool_result.tool_args),
                    "result": tool_result.result,
                }
            )

        raise GameLoopExceededMaxIterationsError(
            tool_calls=tool_calls,
            loop_events=loop_events,
        )

    def _execute_tool(
        self,
        *,
        step_result: AgentLoopStepResult,
        tool_lookup: dict[str, ToolDefinition],
    ) -> ToolExecutionResult:
        tool_name = step_result.tool_name or ""
        tool = tool_lookup.get(tool_name)
        if tool is None:
            raise ValueError(f"Unknown tool requested by provider: {tool_name}")

        try:
            validated_args = tool.validate_args(step_result.tool_args)
            result = tool.invoke(**validated_args)
        except ValueError as exc:
            raise ValueError(f"Invalid arguments for tool '{tool_name}': {exc}") from exc
        except TypeError as exc:
            raise ValueError(
                f"Invalid arguments for tool '{tool_name}': {step_result.tool_args}"
            ) from exc

        logger.info("core_agent.game_loop.tool_executed tool=%s", tool_name)
        return ToolExecutionResult(
            tool_name=tool_name,
            tool_args=dict(validated_args),
            result=result,
        )

    def _validate_step_result(self, step_result: AgentLoopStepResult) -> None:
        if step_result.decision == "call_tool":
            if not step_result.tool_name:
                raise ValueError("Tool decisions must include a tool_name.")
            return

        if step_result.decision == "finish":
            if step_result.kind not in {"answer", "clarification", "fallback"}:
                raise ValueError("Finish decisions must include a valid kind.")
            return

        raise ValueError(f"Unsupported loop decision: {step_result.decision}")
