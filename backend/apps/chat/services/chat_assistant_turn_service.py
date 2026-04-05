from __future__ import annotations

import logging

from apps.chat.models.chat_session import ChatSession
from apps.chat.services.chat_capability_service import ChatCapabilityService
from apps.chat.services.chat_message_service import ChatMessageService
from apps.chat.services.chat_prompt_builder import ChatPromptBuilder
from apps.chat.services.chat_tool_registry_service import ChatToolRegistryService
from apps.core_agent.models.agent_turn_request import AgentTurnRequest
from apps.core_agent.models.agent_turn_result import AgentTurnResult
from apps.core_agent.providers.agent_provider import AgentProvider
from apps.core_agent.providers.agno_openai_provider import AgnoOpenAIProvider


logger = logging.getLogger(__name__)


class ChatAssistantTurnService:
    def __init__(
        self,
        *,
        provider: AgentProvider | None = None,
        prompt_builder: ChatPromptBuilder | None = None,
        capability_service: ChatCapabilityService | None = None,
        tool_registry_service: ChatToolRegistryService | None = None,
        message_service: ChatMessageService | None = None,
    ) -> None:
        self.provider = provider or AgnoOpenAIProvider()
        self.prompt_builder = prompt_builder or ChatPromptBuilder()
        self.capability_service = capability_service or ChatCapabilityService()
        self.tool_registry_service = tool_registry_service or ChatToolRegistryService()
        self.message_service = message_service or ChatMessageService()

    def generate_response(self, *, session: ChatSession, user_prompt: str) -> AgentTurnResult:
        capabilities = self.capability_service.get_release_capabilities()
        tools = self.tool_registry_service.build_tools(user=session.user)
        request = AgentTurnRequest(
            message=user_prompt,
            system_prompt=self.prompt_builder.build_system_prompt(
                session=session,
                capabilities=capabilities,
                user_prompt=user_prompt,
            ),
            history=self.message_service.serialize_history(session),
            tools=tools,
            session_id=str(session.id),
            user_id=str(session.user_id),
            metadata={
                "capabilities": [capability.name for capability in capabilities if capability.enabled],
            },
        )

        logger.info(
            "chat.assistant.turn.started session_id=%s user_id=%s tools=%s",
            session.id,
            session.user_id,
            ",".join(tool.name for tool in tools),
        )
        result = self.provider.run_turn(request)
        logger.info(
            "chat.assistant.turn.completed session_id=%s user_id=%s kind=%s tool_calls=%s",
            session.id,
            session.user_id,
            result.kind,
            len(result.tool_calls),
        )
        return result

    def build_content_blocks(self, result: AgentTurnResult) -> list[dict]:
        block_type = "clarification" if result.kind == "clarification" else "text"
        return [
            {
                "type": block_type,
                "text": result.text,
            }
        ]
