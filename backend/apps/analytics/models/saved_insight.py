from __future__ import annotations

from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.analytics.constants import SUPPORTED_ANALYTICS_QUERY_TYPES


def generate_saved_insight_public_id() -> str:
    return uuid4().hex


class SavedInsight(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_insights",
    )
    public_id = models.CharField(
        max_length=32,
        unique=True,
        default=generate_saved_insight_public_id,
    )
    title = models.CharField(max_length=255)
    summary_text = models.TextField()
    query_definition = models.JSONField()
    chart_payload = models.JSONField()
    last_refreshed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_saved_insight"
        ordering = ["-last_refreshed_at", "-id"]
        indexes = [
            models.Index(fields=["user", "last_refreshed_at"], name="analytics_si_usr_ref_idx"),
        ]

    def __str__(self) -> str:
        return f"saved-insight:{self.public_id} user:{self.user_id}"

    def clean(self) -> None:
        super().clean()
        self._validate_query_definition()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def _validate_query_definition(self) -> None:
        query_definition = self.query_definition
        if not isinstance(query_definition, dict):
            raise ValidationError(
                {
                    "query_definition": "Saved insights require an approved analytics query definition."
                }
            )

        if set(query_definition.keys()) != {"query_type"}:
            raise ValidationError(
                {
                    "query_definition": "Saved insights only support the approved query_type definition shape."
                }
            )

        query_type = query_definition.get("query_type")
        if (
            not isinstance(query_type, str)
            or not query_type.strip()
            or query_type not in SUPPORTED_ANALYTICS_QUERY_TYPES
        ):
            raise ValidationError(
                {"query_definition": "Saved insights only support approved analytics query types."}
            )
