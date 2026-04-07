from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class AgentLoopStepResult:
    decision: Literal["call_tool", "finish"]
    tool_name: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)
    kind: Literal["answer", "clarification", "fallback"] | None = None
    text: str = ""
    content_blocks: list[dict] = field(default_factory=list)
    raw_content: str | None = None
