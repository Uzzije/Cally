from __future__ import annotations

from dataclasses import asdict

from django.utils import timezone

from apps.chat.models.chat_session import ChatSession
from apps.chat.models.message import Message, MessageRole
from apps.core_agent.models.tool_execution_result import ToolExecutionResult


class ChatMessageService:
    def list_messages(self, session: ChatSession):
        return Message.objects.filter(session=session).order_by("created_at", "id")

    def create_user_message(self, session: ChatSession, *, content: str) -> Message:
        message = Message.objects.create(
            session=session,
            role=MessageRole.USER,
            content_blocks=[
                {
                    "type": "text",
                    "text": content,
                }
            ],
        )
        self._touch_session(session)
        return message

    def create_assistant_message(
        self,
        session: ChatSession,
        *,
        content_blocks: list[dict],
        tool_calls: list[ToolExecutionResult] | None = None,
    ) -> Message:
        message = Message.objects.create(
            session=session,
            role=MessageRole.ASSISTANT,
            content_blocks=content_blocks,
            tool_calls=[asdict(tool_call) for tool_call in (tool_calls or [])] or None,
        )
        self._touch_session(session)
        return message

    def serialize_history(self, session: ChatSession) -> list[dict[str, str]]:
        serialized_messages: list[dict[str, str]] = []
        for message in self.list_messages(session):
            serialized_messages.append(
                {
                    "role": message.role,
                    "content": self.render_text_content(message),
                }
            )
        return serialized_messages

    def render_text_content(self, message: Message) -> str:
        parts: list[str] = []
        for block in message.content_blocks:
            if block.get("type") in {"text", "clarification", "status"}:
                text = str(block.get("text", "")).strip()
                if text:
                    parts.append(text)
        return "\n\n".join(parts)

    def _touch_session(self, session: ChatSession) -> None:
        session.updated_at = timezone.now()
        session.save(update_fields=["updated_at"])

