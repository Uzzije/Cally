from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolExecutionResult:
    tool_name: str
    tool_args: dict[str, Any] = field(default_factory=dict)
    result: str | None = None

