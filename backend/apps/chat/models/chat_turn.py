from django.db import models


class ChatTurnStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class ChatTurnResultKind(models.TextChoices):
    ANSWER = "answer", "Answer"
    CLARIFICATION = "clarification", "Clarification"
    FALLBACK = "fallback", "Fallback"
    ERROR = "error", "Error"


class ChatTurnScopeDecision(models.TextChoices):
    IN_SCOPE = "in_scope", "In scope"
    GREETING = "greeting", "Greeting"
    OUT_OF_SCOPE = "out_of_scope", "Out of scope"
    MUTATION_REQUEST = "mutation_request", "Mutation request"
    AMBIGUOUS = "ambiguous", "Ambiguous"


class ChatTurn(models.Model):
    session = models.ForeignKey(
        "chat.ChatSession",
        on_delete=models.CASCADE,
        related_name="turns",
    )
    user_message = models.ForeignKey(
        "chat.Message",
        on_delete=models.CASCADE,
        related_name="initiated_turns",
    )
    assistant_message = models.ForeignKey(
        "chat.Message",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_turns",
    )
    status = models.CharField(
        max_length=32,
        choices=ChatTurnStatus.choices,
        default=ChatTurnStatus.QUEUED,
    )
    result_kind = models.CharField(
        max_length=32,
        choices=ChatTurnResultKind.choices,
        default=ChatTurnResultKind.ERROR,
    )
    scope_decision = models.CharField(
        max_length=32,
        choices=ChatTurnScopeDecision.choices,
        default=ChatTurnScopeDecision.AMBIGUOUS,
    )
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    correlation_id = models.CharField(max_length=64, unique=True)
    trace_events = models.JSONField(default=list)
    eval_snapshot = models.JSONField(default=dict)
    provider_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "chat_turn"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["session", "created_at"], name="chat_turn_session_created_idx"),
            models.Index(fields=["status", "created_at"], name="chat_turn_status_created_idx"),
        ]

    def __str__(self) -> str:
        return f"turn:{self.id} session:{self.session_id} status:{self.status}"
