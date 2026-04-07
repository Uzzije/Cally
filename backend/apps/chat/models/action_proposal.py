from __future__ import annotations

from uuid import uuid4

from django.db import models


def generate_action_proposal_public_id() -> str:
    return uuid4().hex


class ActionProposalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    EXECUTING = "executing", "Executing"
    EXECUTED = "executed", "Executed"
    FAILED = "failed", "Failed"


class ActionProposalType(models.TextChoices):
    CREATE_EVENT = "create_event", "Create event"


class ActionProposal(models.Model):
    session = models.ForeignKey(
        "chat.ChatSession",
        on_delete=models.CASCADE,
        related_name="action_proposals",
    )
    turn = models.ForeignKey(
        "chat.ChatTurn",
        on_delete=models.CASCADE,
        related_name="action_proposals",
    )
    assistant_message = models.ForeignKey(
        "chat.Message",
        on_delete=models.CASCADE,
        related_name="action_proposals",
    )
    public_id = models.CharField(
        max_length=32,
        unique=True,
        default=generate_action_proposal_public_id,
    )
    action_type = models.CharField(
        max_length=32,
        choices=ActionProposalType.choices,
    )
    summary = models.CharField(max_length=255)
    details = models.JSONField(default=dict)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=32,
        choices=ActionProposalStatus.choices,
        default=ActionProposalStatus.PENDING,
    )
    status_detail = models.CharField(max_length=255, null=True, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_action_proposal"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["session", "status"], name="chat_prop_session_status_idx"),
            models.Index(fields=["turn", "created_at"], name="chat_prop_turn_created_idx"),
        ]

    def __str__(self) -> str:
        return f"proposal:{self.public_id} session:{self.session_id} status:{self.status}"
