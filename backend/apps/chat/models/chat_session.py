from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    title = models.CharField(max_length=255, default="New conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_chat_session"
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["user", "updated_at"], name="chat_session_user_updated_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.user_id})"
