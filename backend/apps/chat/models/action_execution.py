from __future__ import annotations

from django.db import models


class ActionExecutionStatus(models.TextChoices):
    EXECUTING = "executing", "Executing"
    EXECUTED = "executed", "Executed"
    FAILED = "failed", "Failed"


class ActionExecution(models.Model):
    proposal = models.ForeignKey(
        "chat.ActionProposal",
        on_delete=models.CASCADE,
        related_name="executions",
    )
    status = models.CharField(
        max_length=32,
        choices=ActionExecutionStatus.choices,
        default=ActionExecutionStatus.EXECUTING,
    )
    result_payload = models.JSONField(default=dict, blank=True)
    failure_reason = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_action_execution"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["proposal", "status"], name="chat_exec_prop_status_idx"),
        ]

    def __str__(self) -> str:
        return f"execution:{self.id} proposal:{self.proposal_id} status:{self.status}"
