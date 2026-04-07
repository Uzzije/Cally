from django.db import models


class ChatRateLimitConfig(models.Model):
    singleton_key = models.CharField(max_length=32, unique=True, default="default")
    daily_message_credit_limit = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_rate_limit_config"

    def __str__(self) -> str:
        return f"ChatRateLimitConfig<{self.daily_message_credit_limit}>"
