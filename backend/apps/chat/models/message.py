from django.db import models


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"


class Message(models.Model):
    session = models.ForeignKey(
        "chat.ChatSession",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=32, choices=MessageRole.choices)
    content_blocks = models.JSONField(default=list)
    tool_calls = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["session", "created_at"], name="chat_msg_session_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.role} ({self.session_id})"
