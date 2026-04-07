from __future__ import annotations

from dataclasses import dataclass
from inspect import cleandoc, getdoc
from typing import Callable, TypeVar

AGENT_TOOL_METADATA_ATTR = "__agent_tool_metadata__"


@dataclass(frozen=True)
class AgentToolMetadata:
    name: str
    description: str


F = TypeVar("F", bound=Callable)


def agent_tool(*, name: str | None = None, description: str | None = None):
    def decorator(func: F) -> F:
        metadata = AgentToolMetadata(
            name=name or func.__name__,
            description=description or cleandoc(getdoc(func) or ""),
        )
        setattr(func, AGENT_TOOL_METADATA_ATTR, metadata)
        return func

    return decorator
