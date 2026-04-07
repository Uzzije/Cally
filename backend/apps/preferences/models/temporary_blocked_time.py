from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.db import models


def generate_temporary_blocked_time_public_id() -> str:
    return uuid4().hex


class TemporaryBlockedTimeSource(models.TextChoices):
    EMAIL_DRAFT = "email_draft", "Email draft"


class TemporaryBlockedTime(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="temporary_blocked_times",
    )
    public_id = models.CharField(
        max_length=32,
        unique=True,
        default=generate_temporary_blocked_time_public_id,
    )
    label = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    timezone = models.CharField(max_length=64)
    source = models.CharField(
        max_length=32,
        choices=TemporaryBlockedTimeSource.choices,
        default=TemporaryBlockedTimeSource.EMAIL_DRAFT,
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "preferences_temporary_blocked_time"
        ordering = ["start_time", "id"]
        indexes = [
            models.Index(fields=["user", "expires_at"], name="pref_temp_block_user_exp_idx"),
            models.Index(fields=["user", "start_time"], name="pref_temp_block_user_start_idx"),
        ]

    def __str__(self) -> str:
        return f"temp-block:{self.public_id} user:{self.user_id}"
