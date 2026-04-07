from __future__ import annotations

from uuid import uuid4

from django.utils import timezone

from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_turn import (
    ChatTurn,
    ChatTurnResultKind,
    ChatTurnScopeDecision,
    ChatTurnStatus,
)
from apps.chat.models.message import Message
from apps.core.types import AuthenticatedUser


class ChatTurnService:
    def create_turn(self, *, session: ChatSession, user_message: Message) -> ChatTurn:
        return ChatTurn.objects.create(
            session=session,
            user_message=user_message,
            correlation_id=uuid4().hex,
            status=ChatTurnStatus.QUEUED,
            result_kind=ChatTurnResultKind.ERROR,
            scope_decision=ChatTurnScopeDecision.AMBIGUOUS,
        )

    def get_user_turn(
        self, user: AuthenticatedUser, *, session_id: int, turn_id: int
    ) -> ChatTurn | None:
        return (
            ChatTurn.objects.select_related("assistant_message", "user_message", "session")
            .filter(session__user=user, session_id=session_id, id=turn_id)
            .first()
        )

    def mark_running(self, turn: ChatTurn) -> ChatTurn:
        turn.status = ChatTurnStatus.RUNNING
        turn.started_at = timezone.now()
        turn.save(update_fields=["status", "started_at"])
        return turn

    def mark_completed(
        self,
        turn: ChatTurn,
        *,
        assistant_message: Message | None,
        result_kind: str,
        scope_decision: str,
        failure_reason: str | None = None,
        provider_metadata: dict | None = None,
        eval_snapshot: dict | None = None,
    ) -> ChatTurn:
        turn.status = ChatTurnStatus.COMPLETED
        turn.assistant_message = assistant_message
        turn.result_kind = result_kind
        turn.scope_decision = scope_decision
        turn.failure_reason = failure_reason
        turn.provider_metadata = provider_metadata or turn.provider_metadata
        turn.eval_snapshot = eval_snapshot or turn.eval_snapshot
        turn.completed_at = timezone.now()
        turn.save(
            update_fields=[
                "status",
                "assistant_message",
                "result_kind",
                "scope_decision",
                "failure_reason",
                "provider_metadata",
                "eval_snapshot",
                "completed_at",
            ]
        )
        return turn

    def mark_failed(
        self, turn: ChatTurn, *, failure_reason: str, eval_snapshot: dict | None = None
    ) -> ChatTurn:
        turn.status = ChatTurnStatus.FAILED
        turn.result_kind = ChatTurnResultKind.ERROR
        turn.failure_reason = failure_reason
        turn.failed_at = timezone.now()
        if eval_snapshot is not None:
            turn.eval_snapshot = eval_snapshot
        turn.save(
            update_fields=["status", "result_kind", "failure_reason", "failed_at", "eval_snapshot"]
        )
        return turn

    def append_trace_event(
        self, turn: ChatTurn, *, event_type: str, summary: str, data: dict | None = None
    ) -> ChatTurn:
        trace_events = list(turn.trace_events)
        trace_events.append(
            {
                "type": event_type,
                "timestamp": timezone.now().isoformat(),
                "summary": summary,
                "data": data or {},
            }
        )
        turn.trace_events = trace_events
        turn.save(update_fields=["trace_events"])
        return turn
