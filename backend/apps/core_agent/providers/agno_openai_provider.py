from __future__ import annotations

import json
from typing import Any, Literal

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from django.conf import settings
from pydantic import BaseModel, Field, model_validator

from apps.core.exceptions import AppConfigurationError
from apps.core_agent.models.agent_loop_step_request import AgentLoopStepRequest
from apps.core_agent.models.agent_loop_step_result import AgentLoopStepResult
from apps.core_agent.providers.agent_provider import AgentProvider


class ActionCardDetails(BaseModel):
    date: str
    time: str
    attendees: list[str]


class ActionCardPayload(BaseModel):
    start_time: str
    end_time: str
    timezone: str
    attendees: list[str] = Field(default_factory=list)
    title: str | None = None


class ActionCardAction(BaseModel):
    id: str
    action_type: Literal["create_event"]
    summary: str
    details: ActionCardDetails
    payload: ActionCardPayload | None = None
    status: Literal["pending", "approved", "rejected", "executed"]


class ActionCardBlock(BaseModel):
    type: Literal["action_card"]
    actions: list[ActionCardAction]


class EmailDraftBlock(BaseModel):
    type: Literal["email_draft"]
    to: list[str]
    cc: list[str] = Field(default_factory=list)
    subject: str
    body: str
    status: Literal["draft"]
    status_detail: str | None = None


class ChartDatum(BaseModel):
    label: str
    value: float


class ChartBlock(BaseModel):
    type: Literal["chart"]
    chart_type: Literal["bar", "line", "pie", "heatmap"]
    title: str
    subtitle: str | None = None
    data: list[ChartDatum]
    save_enabled: bool | None = None


class AgentLoopStructuredResponse(BaseModel):
    decision: Literal["call_tool", "finish"]
    tool_name: str
    tool_args_json: str
    kind: Literal["answer", "clarification", "fallback", ""]
    text: str
    content_blocks: list[ActionCardBlock | EmailDraftBlock | ChartBlock]

    @model_validator(mode="after")
    def validate_decision_payload(self) -> "AgentLoopStructuredResponse":
        if self.decision == "call_tool" and not self.tool_name:
            raise ValueError("call_tool decisions must include tool_name.")

        if self.decision == "call_tool" and self.kind != "":
            raise ValueError("call_tool decisions must set kind to an empty string.")

        if self.decision == "finish" and self.kind == "":
            raise ValueError("finish decisions must include kind.")

        return self


class AgnoOpenAIProvider(AgentProvider):
    default_model_id = "gpt-5-mini"

    def __init__(self, *, api_key: str | None = None, model_id: str | None = None) -> None:
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", None)
        self.model_id = model_id or getattr(settings, "AGNO_MODEL_ID", self.default_model_id)

    def run_step(self, request: AgentLoopStepRequest) -> AgentLoopStepResult:
        if not self.api_key:
            raise AppConfigurationError("OPENAI_API_KEY is required for Agno chat execution.")

        model_id = self.model_id or self.default_model_id
        agent = Agent(
            model=OpenAIChat(id=model_id, api_key=self.api_key),
            system_message=request.system_prompt,
            session_state=request.session_state,
            add_state_in_messages=True,
            response_model=AgentLoopStructuredResponse,
            structured_outputs=True,
            parse_response=True,
            stream=False,
            markdown=False,
            telemetry=False,
            show_tool_calls=False,
        )

        response = agent.run(
            self._build_step_message(request),
            session_id=request.session_id,
            user_id=request.user_id,
            messages=request.history,
        )
        content = self._coerce_step_content(response.content)
        return AgentLoopStepResult(
            decision=content.decision,
            tool_name=content.tool_name,
            tool_args=self._parse_tool_args_json(content.tool_args_json),
            kind=content.kind or None,
            text=content.text,
            content_blocks=[block.model_dump() for block in content.content_blocks],
            raw_content=self._serialize_raw_content(content),
        )

    def _build_step_message(self, request: AgentLoopStepRequest) -> str:
        return "\n\n".join(
            [
                "\n".join(
                    [
                        "## Loop protocol",
                        "- You are deciding the next step in a backend-controlled agent loop.",
                        "- Return exactly one structured decision that matches the response schema.",
                        "- Choose `call_tool` only when one available tool is needed to ground the answer.",
                        "- Choose `finish` only when you can safely return the next user-facing result supported by the schema.",
                        "- Do not invent tools, side effects, or unsupported arguments.",
                        *self._build_mutation_protocol_lines(request.session_state),
                    ]
                ),
                "\n".join(
                    [
                        "## Response shape rules",
                        "- Every response must include all schema fields: decision, tool_name, tool_args_json, kind, text, content_blocks.",
                        "- For `call_tool`: set `decision` to `call_tool`, set `tool_name` to the selected tool, set `tool_args_json` to a JSON object string, set `kind` to an empty string, set `text` to an empty string, and set `content_blocks` to [].",
                        '- Example `call_tool`: {"decision":"call_tool","tool_name":"get_preferences","tool_args_json":"{}","kind":"","text":"","content_blocks":[]}',
                        "- For `finish`: set `decision` to `finish`, set `tool_name` to an empty string, set `tool_args_json` to `{}`, set `kind` to exactly one of `answer`, `clarification`, or `fallback`, include the final `text`, and set `content_blocks` to [] unless returning supported structured blocks.",
                        '- Example `finish`: {"decision":"finish","tool_name":"","tool_args_json":"{}","kind":"answer","text":"Your execution mode is draft_only.","content_blocks":[]}',
                        "- When proposing a calendar mutation, return `finish` with an `action_card`; do not return `call_tool` with `tool_name`=`create_event`.",
                        "- `create_event` action cards should include a `payload` object with `start_time`, `end_time`, `timezone`, and any grounded attendee emails needed for execution.",
                        "- When drafting an email, call `build_email_draft` with `to`, optional `cc`, and one `draft_markdown` string that starts with `Subject:` followed by the body, then finish with a short answer.",
                        "- For supported analytics questions, call `query_analytics`, then finish with a short grounded answer and include the returned `chart` block when helpful.",
                        "- Never omit `kind` on `finish`.",
                    ]
                ),
                "\n".join(
                    [
                        "## Scratchpad",
                        "- Think through GOAL, MEMORY, ENVIRONMENT, ACTION before choosing the next step.",
                        "- Use the conversation history and completed tool calls before reaching for another tool.",
                        "- Prefer finish when the answer is already grounded by prior tool outputs or session state.",
                        "- Base each decision on the current runtime snapshot instead of assumptions.",
                    ]
                ),
                "\n".join(
                    [
                        "## Runtime context snapshot",
                        json.dumps(request.session_state, indent=2, sort_keys=True),
                    ]
                ),
                "\n".join(
                    [
                        "## Time context",
                        json.dumps(
                            self._build_time_context(request.session_state),
                            indent=2,
                            sort_keys=True,
                        ),
                    ]
                ),
                "\n".join(
                    [
                        "## Available tools",
                        json.dumps(
                            [tool.to_prompt_dict() for tool in request.tools],
                            indent=2,
                            sort_keys=True,
                        ),
                    ]
                ),
                "\n".join(
                    [
                        "## Completed tool calls",
                        json.dumps(
                            [
                                {
                                    "tool_name": tool_call.tool_name,
                                    "tool_args": tool_call.tool_args,
                                    "result": self._parse_tool_result(tool_call.result),
                                }
                                for tool_call in request.tool_calls
                            ],
                            indent=2,
                            sort_keys=True,
                        ),
                    ]
                ),
                "\n".join(
                    [
                        "## Loop state",
                        json.dumps(
                            {
                                "iteration": request.iteration,
                                "max_iterations": request.max_iterations,
                                "user_request": request.message,
                                "metadata": request.metadata,
                            },
                            indent=2,
                            sort_keys=True,
                        ),
                    ]
                ),
            ]
        )

    def _parse_tool_result(self, result: str | None) -> Any:
        if result is None:
            return None

        try:
            return json.loads(result)
        except (json.JSONDecodeError, TypeError):
            return result

    def _parse_tool_args_json(self, tool_args_json: str) -> dict[str, Any]:
        if not tool_args_json:
            return {}

        parsed = json.loads(tool_args_json)
        if not isinstance(parsed, dict):
            raise ValueError("tool_args_json must decode to an object.")

        return parsed

    def _serialize_raw_content(self, content: BaseModel | dict | str | None) -> str | None:
        if content is None:
            return None

        if isinstance(content, BaseModel):
            return content.model_dump_json()

        if isinstance(content, dict):
            return json.dumps(content)

        return str(content)

    def _coerce_step_content(self, content: Any) -> AgentLoopStructuredResponse:
        if isinstance(content, AgentLoopStructuredResponse):
            return content

        if isinstance(content, BaseModel):
            return AgentLoopStructuredResponse.model_validate(
                self._normalize_step_payload(content.model_dump())
            )

        if isinstance(content, dict):
            return AgentLoopStructuredResponse.model_validate(self._normalize_step_payload(content))

        if isinstance(content, str):
            return AgentLoopStructuredResponse.model_validate(
                self._normalize_step_payload(json.loads(content))
            )

        raise ValueError("Agno response content did not match the expected loop response model.")

    def _normalize_step_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        decision = normalized.get("decision", "")

        if normalized.get("tool_name") is None:
            normalized["tool_name"] = ""
        if normalized.get("tool_args_json") in {None, ""}:
            normalized["tool_args_json"] = "{}"
        if normalized.get("text") is None:
            normalized["text"] = ""
        if normalized.get("content_blocks") is None:
            normalized["content_blocks"] = []

        if decision == "call_tool":
            if normalized.get("kind") is None:
                normalized["kind"] = ""
        elif decision == "finish":
            if normalized.get("kind") in {None, ""}:
                normalized["kind"] = "answer"

        return normalized

    def _build_time_context(self, session_state: dict[str, Any]) -> dict[str, Any]:
        workspace = session_state.get("workspace", {})
        return {
            "default_timezone": workspace.get("default_timezone"),
            "current_time": workspace.get("current_time"),
            "current_date": workspace.get("current_date"),
            "current_weekday": workspace.get("current_weekday"),
        }

    def _build_mutation_protocol_lines(self, session_state: dict[str, Any]) -> list[str]:
        execution_profile = session_state.get("execution_profile", {})
        mutation_mode = execution_profile.get("mutation_mode")
        if mutation_mode == "direct_tool_call":
            return [
                "- When direct mutation tools are available and the request is fully grounded, you may use them.",
                "- After a successful direct mutation tool call, finish with an answer grounded by that tool result.",
                "- `build_email_draft` is the callable tool for draft-only scheduling email previews.",
                "- When the user asks for a scheduling email draft, call `build_email_draft` once the recipient and purpose are grounded.",
                "- Provide the draft as one markdown string in `draft_markdown`: a `Subject:` line, a blank line, then the body.",
                "- `query_analytics` is the callable tool for supported read-only analytics over synced calendar data.",
                "- When the user asks a supported analytics question, call `query_analytics` before returning a chart-backed answer.",
                f"- {execution_profile.get('grounded_mutation_finish_instruction', '')}".rstrip(),
            ]

        return [
            "- `create_event` is an action type for `action_card` content, not a callable tool name.",
            "- When proposing a calendar mutation, return `finish` with an `action_card`; do not return `call_tool` with `tool_name`=`create_event`.",
            "- `build_email_draft` is the callable tool for draft-only scheduling email previews.",
            "- When the user asks for a scheduling email draft, call `build_email_draft` once the recipient and purpose are grounded.",
            "- Provide the draft as one markdown string in `draft_markdown`: a `Subject:` line, a blank line, then the body.",
            "- `query_analytics` is the callable tool for supported read-only analytics over synced calendar data.",
            "- When the user asks a supported analytics question, call `query_analytics` before returning a chart-backed answer.",
            f"- {execution_profile.get('grounded_mutation_finish_instruction', '')}".rstrip(),
        ]
