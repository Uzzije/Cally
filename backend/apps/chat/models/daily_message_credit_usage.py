from django.conf import settings
from django.db import models


class DailyMessageCreditUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_message_credit_usages",
    )
    usage_date = models.DateField()
    used_credits = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_daily_message_credit_usage"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "usage_date"],
                name="chat_daily_message_credit_usage_user_usage_date_uniq",
            )
        ]

    def __str__(self) -> str:
        return f"DailyMessageCreditUsage<{self.user_id}:{self.usage_date}>"
