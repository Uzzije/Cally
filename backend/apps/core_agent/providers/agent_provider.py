from abc import ABC, abstractmethod

from apps.core_agent.models.agent_turn_request import AgentTurnRequest
from apps.core_agent.models.agent_turn_result import AgentTurnResult


class AgentProvider(ABC):
    @abstractmethod
    def run_turn(self, request: AgentTurnRequest) -> AgentTurnResult:
        raise NotImplementedError

