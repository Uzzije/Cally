from __future__ import annotations

from apps.chat.models.chat_session import ChatSession
from apps.core.types import AuthenticatedUser


class ChatSessionService:
    default_title = "New conversation"

    def list_sessions(self, user: AuthenticatedUser):
        return ChatSession.objects.filter(user=user).order_by("-updated_at", "-id")

    def create_session(self, user: AuthenticatedUser, *, title: str | None = None) -> ChatSession:
        return ChatSession.objects.create(
            user=user,
            title=title or self.default_title,
        )

    def get_user_session(self, user: AuthenticatedUser, *, session_id: int) -> ChatSession | None:
        return ChatSession.objects.filter(user=user, id=session_id).first()

    def assign_title_from_message(self, session: ChatSession, *, message_text: str) -> ChatSession:
        if session.title != self.default_title:
            return session

        normalized_title = " ".join(message_text.strip().split())
        if not normalized_title:
            return session

        if len(normalized_title) > 48:
            normalized_title = f"{normalized_title[:45].rstrip()}..."

        session.title = normalized_title
        session.save(update_fields=["title", "updated_at"])
        return session
