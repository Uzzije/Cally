from dataclasses import dataclass


@dataclass(frozen=True)
class AgentCapability:
    name: str
    description: str
    enabled: bool = True
