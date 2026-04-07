from dataclasses import dataclass, field
from typing import Any

from apps.core_agent.models.tool_definition import ToolDefinition


@dataclass(frozen=True)
class AgentTurnRequest:
    message: str
    system_prompt: str
    history: list[dict[str, str]] = field(default_factory=list)
    tools: list[ToolDefinition] = field(default_factory=list)
    session_state: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
