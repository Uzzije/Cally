from __future__ import annotations

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.calendars.services.calendar_event_mutation_service import (
    CalendarEventMutationError,
    CalendarEventMutationRequest,
    CalendarEventMutationService,
)
from apps.chat.models.action_execution import ActionExecution, ActionExecutionStatus
from apps.chat.models.action_proposal import (
    ActionProposal,
    ActionProposalStatus,
    generate_action_proposal_public_id,
)
from apps.chat.models.chat_session import ChatSession
from apps.chat.models.chat_turn import ChatTurn
from apps.chat.models.message import Message
from apps.chat.services.chat_execution_policy_service import ChatExecutionPolicyService
from apps.core.types import AuthenticatedUser

logger = logging.getLogger(__name__)


class ActionProposalError(Exception):
    pass


class ActionProposalNotFoundError(ActionProposalError):
    pass


class ActionProposalConflictError(ActionProposalError):
    pass


class ActionProposalPolicyError(ActionProposalError):
    pass


class ActionProposalPayloadError(ActionProposalPolicyError):
    pass


class ChatActionProposalService:
    def __init__(
        self,
        *,
        execution_policy_service: ChatExecutionPolicyService | None = None,
        calendar_event_mutation_service: CalendarEventMutationService | None = None,
    ) -> None:
        """Persist action_card proposals and execute approved calendar mutations."""
        self.execution_policy_service = execution_policy_service or ChatExecutionPolicyService()
        self.calendar_event_mutation_service = (
            calendar_event_mutation_service or CalendarEventMutationService()
        )

    def persist_from_message(
        self,
        *,
        session: ChatSession,
        turn: ChatTurn,
        assistant_message: Message,
    ) -> list[ActionProposal]:
        """Extract action_card blocks from an assistant message and persist them as ActionProposals."""
        content_blocks = assistant_message.content_blocks
        created_proposals: list[ActionProposal] = []
        has_updates = False

        for block in content_blocks:
            if block.get("type") != "action_card":
                continue

            actions = block.get("actions", [])
            if not isinstance(actions, list):
                continue

            for action in actions:
                public_id = generate_action_proposal_public_id()
                payload = action.pop("payload", {})
                action["id"] = public_id
                has_updates = True
                created_proposals.append(
                    ActionProposal.objects.create(
                        session=session,
                        turn=turn,
                        assistant_message=assistant_message,
                        public_id=public_id,
                        action_type=action["action_type"],
                        summary=action["summary"],
                        details=action["details"],
                        payload=payload if isinstance(payload, dict) else {},
                        status=action["status"],
                    )
                )

        if has_updates:
            assistant_message.content_blocks = content_blocks
            assistant_message.save(update_fields=["content_blocks"])

        return created_proposals

    def get_user_proposal(
        self, user: AuthenticatedUser, *, session_id: int, proposal_id: str
    ) -> ActionProposal:
        """Fetch a proposal by public id scoped to the owning user + session."""
        proposal = (
            ActionProposal.objects.select_related("session", "assistant_message")
            .filter(session__user=user, session_id=session_id, public_id=proposal_id)
            .first()
        )
        if proposal is None:
            raise ActionProposalNotFoundError("Proposal not found.")

        return proposal

    def reject_proposal(
        self, user: AuthenticatedUser, *, session_id: int, proposal_id: str
    ) -> ActionProposal:
        """Reject a pending proposal and update the originating assistant message block state."""
        proposal = self.get_user_proposal(user, session_id=session_id, proposal_id=proposal_id)
        if proposal.status != ActionProposalStatus.PENDING:
            raise ActionProposalConflictError("Only pending proposals can be rejected.")

        proposal.status = ActionProposalStatus.REJECTED
        proposal.status_detail = "Rejected. No calendar changes were made."
        proposal.result_payload = {}
        proposal.save(update_fields=["status", "status_detail", "result_payload", "updated_at"])
        self._touch_session(proposal.session)
        self._sync_message_action_state(proposal)

        logger.info(
            "chat.proposal.rejected session_id=%s user_id=%s proposal_id=%s",
            proposal.session_id,
            proposal.session.user_id,
            proposal.public_id,
        )
        return proposal

    def approve_proposal(
        self, user: AuthenticatedUser, *, session_id: int, proposal_id: str
    ) -> ActionProposal:
        """Approve and execute a pending proposal, reconciling results back into message + DB."""
        proposal = self.get_user_proposal(user, session_id=session_id, proposal_id=proposal_id)
        if proposal.status != ActionProposalStatus.PENDING:
            raise ActionProposalConflictError("Only pending proposals can be approved.")

        decision = self.execution_policy_service.evaluate(user=user, proposal=proposal)
        if not decision.allowed:
            raise ActionProposalPolicyError(decision.reason or "This proposal cannot be executed.")

        calendar_request = self._build_calendar_request(proposal)

        proposal.status = ActionProposalStatus.APPROVED
        proposal.status_detail = "Approval received. Preparing the calendar change."
        proposal.save(update_fields=["status", "status_detail", "updated_at"])
        self._touch_session(proposal.session)
        self._sync_message_action_state(proposal)

        execution = ActionExecution.objects.create(proposal=proposal)
        proposal.status = ActionProposalStatus.EXECUTING
        proposal.status_detail = "Creating the event on your primary calendar."
        proposal.save(update_fields=["status", "status_detail", "updated_at"])
        self._sync_message_action_state(proposal)

        logger.info(
            "chat.proposal.execution_started session_id=%s user_id=%s proposal_id=%s",
            proposal.session_id,
            proposal.session.user_id,
            proposal.public_id,
        )

        try:
            mutation_result = self.calendar_event_mutation_service.create_primary_calendar_event(
                user,
                request=calendar_request,
            )
        except CalendarEventMutationError as exc:
            execution.status = ActionExecutionStatus.FAILED
            execution.failure_reason = str(exc)
            execution.result_payload = {}
            execution.save(
                update_fields=["status", "failure_reason", "result_payload", "updated_at"]
            )

            proposal.status = ActionProposalStatus.FAILED
            proposal.status_detail = "We couldn’t create that event. Please try again."
            proposal.result_payload = {}
            proposal.save(update_fields=["status", "status_detail", "result_payload", "updated_at"])
            self._sync_message_action_state(proposal)

            logger.warning(
                "chat.proposal.execution_failed session_id=%s user_id=%s proposal_id=%s reason=%s",
                proposal.session_id,
                proposal.session.user_id,
                proposal.public_id,
                str(exc),
            )
            return proposal

        result_payload = {
            "event_id": mutation_result.event_id,
            "google_event_id": mutation_result.google_event_id,
        }
        execution.status = ActionExecutionStatus.EXECUTED
        execution.failure_reason = None
        execution.result_payload = result_payload
        execution.save(update_fields=["status", "failure_reason", "result_payload", "updated_at"])

        proposal.status = ActionProposalStatus.EXECUTED
        proposal.status_detail = "Added to your primary calendar."
        proposal.result_payload = result_payload
        proposal.save(update_fields=["status", "status_detail", "result_payload", "updated_at"])
        self._sync_message_action_state(proposal)

        logger.info(
            "chat.proposal.executed session_id=%s user_id=%s proposal_id=%s event_id=%s google_event_id=%s",
            proposal.session_id,
            proposal.session.user_id,
            proposal.public_id,
            mutation_result.event_id,
            mutation_result.google_event_id,
        )
        return proposal

    def serialize(self, proposal: ActionProposal) -> dict[str, Any]:
        """Serialize a proposal into an API-friendly shape."""
        return {
            "id": proposal.public_id,
            "status": proposal.status,
            "action_type": proposal.action_type,
            "summary": proposal.summary,
            "details": proposal.details,
            "status_detail": proposal.status_detail,
            "result": proposal.result_payload or None,
        }

    def _build_calendar_request(self, proposal: ActionProposal) -> CalendarEventMutationRequest:
        payload = proposal.payload or {}
        if not payload:
            raise ActionProposalPayloadError(
                "This proposal is missing execution details. Please ask me to draft it again."
            )

        missing_fields = [
            field_name for field_name in ["start_time", "end_time"] if not payload.get(field_name)
        ]
        if missing_fields:
            missing_display = ", ".join(missing_fields)
            raise ActionProposalPayloadError(
                f"This proposal is missing execution details ({missing_display}). Please ask me to draft it again."
            )

        return CalendarEventMutationRequest(
            title=str(payload.get("title") or proposal.summary),
            start_time=str(payload["start_time"]),
            end_time=str(payload["end_time"]),
            timezone=str(payload.get("timezone") or timezone.get_current_timezone_name()),
            attendee_emails=self._filter_attendee_emails(payload.get("attendees", [])),
        )

    def _filter_attendee_emails(self, attendees: list[Any]) -> list[str]:
        if not isinstance(attendees, list):
            return []

        return [
            attendee.strip()
            for attendee in attendees
            if isinstance(attendee, str) and "@" in attendee and attendee.strip()
        ]

    def _sync_message_action_state(self, proposal: ActionProposal) -> None:
        content_blocks = proposal.assistant_message.content_blocks

        for block in content_blocks:
            if block.get("type") != "action_card":
                continue

            actions = block.get("actions", [])
            if not isinstance(actions, list):
                continue

            for action in actions:
                if action.get("id") != proposal.public_id:
                    continue

                action["status"] = proposal.status
                if proposal.status_detail:
                    action["status_detail"] = proposal.status_detail
                else:
                    action.pop("status_detail", None)

                if proposal.result_payload:
                    action["result"] = proposal.result_payload
                else:
                    action.pop("result", None)

        proposal.assistant_message.content_blocks = content_blocks
        proposal.assistant_message.save(update_fields=["content_blocks"])

    def _touch_session(self, session: ChatSession) -> None:
        session.updated_at = timezone.now()
        session.save(update_fields=["updated_at"])
