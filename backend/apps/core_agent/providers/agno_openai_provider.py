from __future__ import annotations

import json

from django.conf import settings

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from apps.core.exceptions import AppConfigurationError
from apps.core_agent.models.agent_turn_request import AgentTurnRequest
from apps.core_agent.models.agent_turn_result import AgentTurnResult
from apps.core_agent.models.tool_execution_result import ToolExecutionResult
from apps.core_agent.providers.agent_provider import AgentProvider


class AgnoOpenAIProvider(AgentProvider):
    default_model_id = "gpt-4o-mini"

    def __init__(self, *, api_key: str | None = None, model_id: str | None = None) -> None:
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", None)
        self.model_id = model_id or getattr(settings, "AGNO_MODEL_ID", self.default_model_id)

    def run_turn(self, request: AgentTurnRequest) -> AgentTurnResult:
        if not self.api_key:
            raise AppConfigurationError("OPENAI_API_KEY is required for Agno chat execution.")

        agent = Agent(
            model=OpenAIChat(id=self.model_id, api_key=self.api_key),
            system_message=request.system_prompt,
            tools=[tool.handler for tool in request.tools],
            stream=False,
            markdown=False,
            telemetry=False,
            show_tool_calls=True,
        )

        response = agent.run(
            request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            messages=request.history,
        )

        parsed_payload = self._parse_payload(response.content)
        return AgentTurnResult(
            kind=parsed_payload["kind"],
            text=parsed_payload["text"],
            raw_content=str(response.content) if response.content is not None else None,
            tool_calls=[
                ToolExecutionResult(
                    tool_name=tool_execution.tool_name or "",
                    tool_args=tool_execution.tool_args or {},
                    result=tool_execution.result,
                )
                for tool_execution in (response.tools or [])
            ],
        )

    def _parse_payload(self, content) -> dict[str, str]:
        if isinstance(content, dict):
            payload = content
        else:
            try:
                payload = json.loads(content)
            except (TypeError, json.JSONDecodeError):
                payload = {"kind": "answer", "text": str(content).strip()}

        kind = payload.get("kind", "answer")
        text = str(payload.get("text", "")).strip()
        if kind not in {"answer", "clarification", "fallback"}:
            kind = "answer"
        if not text:
            text = "I couldn't produce a grounded response for that request."
            kind = "fallback"
        return {"kind": kind, "text": text}

