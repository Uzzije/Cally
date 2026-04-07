from abc import ABC, abstractmethod

from apps.core_agent.models.agent_loop_step_request import AgentLoopStepRequest
from apps.core_agent.models.agent_loop_step_result import AgentLoopStepResult


class AgentProvider(ABC):
    @abstractmethod
    def run_step(self, request: AgentLoopStepRequest) -> AgentLoopStepResult:
        raise NotImplementedError
