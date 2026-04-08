from __future__ import annotations

from dataclasses import asdict

from django.utils import timezone

from apps.chat.models.chat_session import ChatSession
from apps.chat.models.message import Message, MessageRole
from apps.chat.services.chat_content_block_validation_service import (
    ChatContentBlockValidationService,
)
from apps.core_agent.models.tool_execution_result import ToolExecutionResult


class ChatMessageService:
    def __init__(
        self,
        *,
        content_block_validation_service: ChatContentBlockValidationService | None = None,
    ) -> None:
        self.content_block_validation_service = (
            content_block_validation_service or ChatContentBlockValidationService()
        )

    def list_messages(self, session: ChatSession):
        """Return the session's messages in stable chronological order."""
        return Message.objects.filter(session=session).order_by("created_at", "id")

    def create_user_message(self, session: ChatSession, *, content: str) -> Message:
        """Persist a user text message and bump the session's `updated_at`."""
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
        """Persist an assistant message after validating content blocks and serializing tool calls."""
        validated_content_blocks = self.content_block_validation_service.validate(content_blocks)
        message = Message.objects.create(
            session=session,
            role=MessageRole.ASSISTANT,
            content_blocks=validated_content_blocks,
            tool_calls=[asdict(tool_call) for tool_call in (tool_calls or [])] or None,
        )
        self._touch_session(session)
        return message

    def serialize_history(
        self,
        session: ChatSession,
        *,
        limit: int | None = None,
    ) -> list[dict[str, str]]:
        """Serialize chat history into provider-friendly role/content pairs."""
        serialized_messages: list[dict[str, str]] = []
        messages = self.list_messages(session)
        if limit is not None:
            messages = reversed(list(messages.order_by("-created_at", "-id")[:limit]))

        for message in messages:
            serialized_messages.append(
                {
                    "role": message.role,
                    "content": self.render_text_content(message),
                }
            )
        return serialized_messages

    def render_text_content(self, message: Message) -> str:
        """Render heterogeneous content blocks into a single plain-text summary for LLM context."""
        parts: list[str] = []
        for block in message.content_blocks:
            if block.get("type") in {"text", "clarification", "status"}:
                text = str(block.get("text", "")).strip()
                if text:
                    parts.append(text)
                continue

            if block.get("type") == "email_draft":
                draft_summary = self._render_email_draft_summary(block)
                if draft_summary:
                    parts.append(draft_summary)
                continue

            if block.get("type") == "chart":
                chart_summary = self._render_chart_summary(block)
                if chart_summary:
                    parts.append(chart_summary)
        return "\n\n".join(parts)

    def _render_email_draft_summary(self, block: dict) -> str:
        to_recipients = block.get("to") or []
        cc_recipients = block.get("cc") or []
        subject = str(block.get("subject", "")).strip()
        body = str(block.get("body", "")).strip()

        if not to_recipients or not subject or not body:
            return ""

        lines = [
            "Email draft",
            f"To: {', '.join(str(recipient) for recipient in to_recipients)}",
        ]
        if cc_recipients:
            lines.append(f"Cc: {', '.join(str(recipient) for recipient in cc_recipients)}")
        lines.append(f"Subject: {subject}")
        lines.append("")
        lines.append(body)
        return "\n".join(lines)

    def _render_chart_summary(self, block: dict) -> str:
        title = str(block.get("title", "")).strip()
        chart_type = str(block.get("chart_type", "")).strip()
        data = block.get("data") or []

        if not title or not chart_type or not data:
            return ""

        rendered_points = ", ".join(
            f"{point.get('label')}: {point.get('value')}"
            for point in data[:4]
            if isinstance(point, dict)
        )
        return f"Chart ({chart_type}): {title}\n{rendered_points}".strip()

    def _touch_session(self, session: ChatSession) -> None:
        """Update `updated_at` so the session reflects new activity."""
        session.updated_at = timezone.now()
        session.save(update_fields=["updated_at"])
