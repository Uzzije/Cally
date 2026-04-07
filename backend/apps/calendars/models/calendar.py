from django.conf import settings
from django.db import models


class Calendar(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendars",
    )
    google_calendar_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)
    color = models.CharField(max_length=32, blank=True)
    timezone = models.CharField(max_length=64, blank=True)
    sync_token = models.TextField(blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    webhook_channel_id = models.CharField(max_length=255, blank=True)
    webhook_resource_id = models.CharField(max_length=255, blank=True)
    webhook_channel_token = models.CharField(max_length=255, blank=True)
    webhook_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "calendars_calendar"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "google_calendar_id"],
                name="calendars_calendar_user_google_calendar_id_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.user_id})"
