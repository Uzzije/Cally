from __future__ import annotations

import json
import logging

from apps.chat.models.chat_session import ChatSession
from apps.chat.services.chat_agent_context_service import ChatAgentContextService
from apps.chat.services.chat_capability_service import ChatCapabilityService
from apps.chat.services.chat_content_block_validation_service import (
    ChatContentBlockValidationService,
)
from apps.chat.services.chat_execution_mode_profile_service import ChatExecutionModeProfileService
from apps.chat.services.chat_message_service import ChatMessageService
from apps.chat.services.chat_prompt_builder import ChatPromptBuilder
from apps.chat.services.chat_tool_registry_service import ChatToolRegistryService
from apps.core_agent.models.agent_turn_request import AgentTurnRequest
from apps.core_agent.models.agent_turn_result import AgentTurnResult
from apps.core_agent.providers.agent_provider import AgentProvider
from apps.core_agent.providers.agno_openai_provider import AgnoOpenAIProvider
from apps.core_agent.services.game_loop_service import GameLoopService

logger = logging.getLogger(__name__)


class ChatAssistantTurnService:
    history_message_limit = 24

    def __init__(
        self,
        *,
        provider: AgentProvider | None = None,
        prompt_builder: ChatPromptBuilder | None = None,
        capability_service: ChatCapabilityService | None = None,
        execution_mode_profile_service: ChatExecutionModeProfileService | None = None,
        tool_registry_service: ChatToolRegistryService | None = None,
        agent_context_service: ChatAgentContextService | None = None,
        message_service: ChatMessageService | None = None,
        game_loop_service: GameLoopService | None = None,
    ) -> None:
        """Assemble prompt/tools/session_state and run one assistant turn through the agent game loop."""
        self.provider = provider or AgnoOpenAIProvider()
        self.prompt_builder = prompt_builder or ChatPromptBuilder()
        self.capability_service = capability_service or ChatCapabilityService()
        self.execution_mode_profile_service = (
            execution_mode_profile_service or ChatExecutionModeProfileService()
        )
        self.tool_registry_service = tool_registry_service or ChatToolRegistryService()
        self.agent_context_service = agent_context_service or ChatAgentContextService()
        self.message_service = message_service or ChatMessageService()
        self.game_loop_service = game_loop_service or GameLoopService(provider=self.provider)

    def generate_response(self, *, session: ChatSession, user_prompt: str) -> AgentTurnResult:
        """Build an AgentTurnRequest from the chat session and run it through the provider loop."""
        capabilities = self.capability_service.get_release_capabilities()
        execution_profile = self.execution_mode_profile_service.get_profile(session.user)
        tools = self.tool_registry_service.build_tools(user=session.user, profile=execution_profile)
        session_state = self.agent_context_service.build_session_state(
            session=session,
            capabilities=capabilities,
            tools=tools,
            execution_profile=execution_profile,
        )
        total_messages = self.message_service.list_messages(session).count()
        history = self.message_service.serialize_history(
            session,
            limit=self.history_message_limit,
        )
        request = AgentTurnRequest(
            message=self.prompt_builder.build_user_prompt(user_prompt=user_prompt),
            system_prompt=self.prompt_builder.build_system_prompt(profile=execution_profile),
            history=history,
            tools=tools,
            session_state=session_state,
            session_id=str(session.id),
            user_id=str(session.user_id),
            metadata={
                "capabilities": [
                    capability.name for capability in capabilities if capability.enabled
                ],
            },
        )

        logger.info(
            "chat.assistant.turn.started session_id=%s user_id=%s tools=%s history_messages=%s/%s",
            session.id,
            session.user_id,
            ",".join(tool.name for tool in tools),
            len(history),
            total_messages,
        )
        result = self.game_loop_service.run(request)
        logger.info(
            "chat.assistant.turn.completed session_id=%s user_id=%s kind=%s tool_calls=%s",
            session.id,
            session.user_id,
            result.kind,
            len(result.tool_calls),
        )
        return result

    def build_content_blocks(self, result: AgentTurnResult) -> list[dict]:
        """Map the agent result into validated content blocks for persistence and UI rendering."""
        if result.content_blocks:
            return result.content_blocks

        analytics_blocks = self._extract_analytics_blocks_from_tool_calls(result)
        if analytics_blocks is not None:
            analytics_content_blocks: list[dict] = []
            if result.text.strip():
                analytics_content_blocks.append(
                    {
                        "type": "text",
                        "text": result.text,
                    }
                )
            else:
                analytics_content_blocks.append(
                    {
                        "type": "text",
                        "text": analytics_blocks["summary_text"],
                    }
                )
            analytics_content_blocks.append(analytics_blocks["chart_block"])
            return analytics_content_blocks

        email_draft_block = self._extract_email_draft_block_from_tool_calls(result)
        if email_draft_block is not None:
            email_content_blocks: list[dict] = []
            if result.text.strip():
                email_content_blocks.append(
                    {
                        "type": "text",
                        "text": result.text,
                    }
                )
            email_content_blocks.append(email_draft_block)
            return email_content_blocks

        block_type = "clarification" if result.kind == "clarification" else "text"
        return [
            {
                "type": block_type,
                "text": result.text,
            }
        ]

    def _extract_email_draft_block_from_tool_calls(self, result: AgentTurnResult) -> dict | None:
        validator = ChatContentBlockValidationService()
        for tool_call in reversed(result.tool_calls):
            if tool_call.tool_name != "build_email_draft" or not tool_call.result:
                continue

            try:
                payload = json.loads(tool_call.result)
            except json.JSONDecodeError:
                logger.warning("chat.assistant.turn.invalid_email_draft_tool_payload")
                return None

            try:
                validator.validate([payload])
            except ValueError:
                logger.warning("chat.assistant.turn.rejected_email_draft_tool_payload")
                return None

            if payload.get("type") == "email_draft":
                return payload

        return None

    def _extract_analytics_blocks_from_tool_calls(self, result: AgentTurnResult) -> dict | None:
        validator = ChatContentBlockValidationService()
        for tool_call in reversed(result.tool_calls):
            if tool_call.tool_name != "query_analytics" or not tool_call.result:
                continue

            try:
                payload = json.loads(tool_call.result)
            except json.JSONDecodeError:
                logger.warning("chat.assistant.turn.invalid_analytics_tool_payload")
                return None

            if not isinstance(payload, dict):
                logger.warning("chat.assistant.turn.invalid_analytics_tool_shape")
                return None

            summary_text = payload.get("summary_text")
            chart_block = payload.get("chart_block")
            if not isinstance(summary_text, str) or not summary_text.strip():
                logger.warning("chat.assistant.turn.invalid_analytics_summary")
                return None
            if not isinstance(chart_block, dict):
                logger.warning("chat.assistant.turn.invalid_chart_tool_shape")
                return None

            try:
                validator.validate([chart_block])
            except ValueError:
                logger.warning("chat.assistant.turn.rejected_chart_tool_payload")
                return None

            if chart_block.get("type") == "chart":
                return {
                    "summary_text": summary_text.strip(),
                    "chart_block": chart_block,
                }

        return None
