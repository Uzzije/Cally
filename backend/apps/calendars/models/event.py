from django.db import models


class Event(models.Model):
    calendar = models.ForeignKey(
        "calendars.Calendar",
        on_delete=models.CASCADE,
        related_name="events",
    )
    google_event_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    timezone = models.CharField(max_length=64, blank=True)
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, blank=True)
    attendees = models.JSONField(default=list, blank=True)
    organizer_email = models.EmailField(blank=True)
    is_all_day = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "calendars_event"
        constraints = [
            models.UniqueConstraint(
                fields=["calendar", "google_event_id"],
                name="calendars_event_calendar_google_event_id_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["calendar", "start_time"], name="cal_event_start_idx"),
            models.Index(fields=["calendar", "end_time"], name="cal_event_end_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.start_time.isoformat()})"
