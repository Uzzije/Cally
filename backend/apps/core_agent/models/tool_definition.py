from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: Callable[..., str]

    def invoke(self, **kwargs) -> str:
        return self.handler(**kwargs)

