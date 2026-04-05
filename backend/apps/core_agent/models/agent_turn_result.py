from dataclasses import dataclass, field

from apps.core_agent.models.tool_execution_result import ToolExecutionResult


@dataclass(frozen=True)
class AgentTurnResult:
    kind: str
    text: str
    tool_calls: list[ToolExecutionResult] = field(default_factory=list)
    raw_content: str | None = None

