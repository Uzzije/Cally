from django.conf import settings
from django.db import models


class ExecutionMode(models.TextChoices):
    DRAFT_ONLY = "draft_only", "Draft only"
    CONFIRM = "confirm", "Confirm before executing"


class UserPreferences(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    execution_mode = models.CharField(
        max_length=32,
        choices=ExecutionMode.choices,
        default=ExecutionMode.DRAFT_ONLY,
    )
    display_timezone = models.CharField(max_length=64, blank=True, default="")
    blocked_times = models.JSONField(default=list, blank=True)
    email_send_limit_per_hour = models.PositiveIntegerField(default=20)
    event_create_limit_per_hour = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "preferences_user_preferences"

    def __str__(self) -> str:
        return f"Preferences<{self.user_id}>"
