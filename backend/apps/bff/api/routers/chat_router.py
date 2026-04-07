import logging

from ninja import Router

from apps.core.api.auth import session_auth
from apps.bff.api.schemas.chat_action_proposal_response_schema import (
    ChatActionProposalResponseSchema,
)
from apps.bff.api.schemas.chat_credit_status_response_schema import ChatCreditStatusResponseSchema
from apps.bff.api.schemas.chat_message_history_response_schema import (
    ChatMessageHistoryResponseSchema,
)
from apps.bff.api.schemas.chat_message_response_schema import ChatMessageResponseSchema
from apps.bff.api.schemas.chat_session_response_schema import ChatSessionResponseSchema
from apps.bff.api.schemas.chat_sessions_response_schema import ChatSessionsResponseSchema
from apps.bff.api.schemas.chat_submit_accepted_response_schema import (
    ChatSubmitAcceptedResponseSchema,
)
from apps.bff.api.schemas.chat_submit_message_request_schema import ChatSubmitMessageRequestSchema
from apps.bff.api.schemas.chat_turn_response_schema import ChatTurnResponseSchema
from apps.bff.api.schemas.chat_turn_status_response_schema import ChatTurnStatusResponseSchema
from apps.bff.api.schemas.error_response_schema import ErrorResponseSchema
from apps.chat.services.chat_action_proposal_service import (
    ActionProposalConflictError,
    ActionProposalNotFoundError,
    ActionProposalPolicyError,
    ChatActionProposalService,
)
from apps.chat.services.chat_message_service import ChatMessageService
from apps.chat.services.chat_message_credit_service import (
    ChatMessageCreditLimitExceededError,
    ChatMessageCreditService,
)
from apps.chat.services.chat_session_service import ChatSessionService
from apps.chat.services.chat_turn_service import ChatTurnService
from apps.chat.services.chat_turn_trigger_service import ChatTurnTriggerService

logger = logging.getLogger(__name__)

router = Router(tags=["chat"], auth=session_auth)


def _serialize_session(session):
    return ChatSessionResponseSchema(
        id=session.id,
        title=session.title,
        updated_at=session.updated_at.isoformat(),
    )


def _serialize_message(message):
    return ChatMessageResponseSchema(
        id=message.id,
        role=message.role,
        content_blocks=message.content_blocks,
        created_at=message.created_at.isoformat(),
    )


def _serialize_turn(turn):
    return ChatTurnResponseSchema(
        id=turn.id,
        status=turn.status,
        result_kind=turn.result_kind,
        scope_decision=turn.scope_decision,
        failure_reason=turn.failure_reason,
        trace_events=turn.trace_events,
        created_at=turn.created_at.isoformat(),
        completed_at=turn.completed_at.isoformat() if turn.completed_at else None,
    )


def _serialize_proposal(proposal):
    return ChatActionProposalResponseSchema(
        id=proposal.public_id,
        status=proposal.status,
        action_type=proposal.action_type,
        summary=proposal.summary,
        details=proposal.details,
        status_detail=proposal.status_detail,
        result=proposal.result_payload or None,
    )


@router.get(
    "chat/credits",
    response={200: ChatCreditStatusResponseSchema, 401: ErrorResponseSchema},
)
def get_chat_credits(request):
    status = ChatMessageCreditService().get_status(request.user)
    return ChatCreditStatusResponseSchema(
        limit=status.limit,
        used=status.used,
        remaining=status.remaining,
        usage_date=status.usage_date,
    )


@router.get(
    "chat/sessions",
    response={200: ChatSessionsResponseSchema, 401: ErrorResponseSchema},
)
def list_chat_sessions(request):
    sessions = ChatSessionService().list_sessions(request.user)
    return ChatSessionsResponseSchema(
        sessions=[_serialize_session(session) for session in sessions],
    )


@router.post(
    "chat/sessions",
    response={200: ChatSessionResponseSchema, 401: ErrorResponseSchema},
)
def create_chat_session(request):
    session = ChatSessionService().create_session(request.user)
    return _serialize_session(session)


@router.get(
    "chat/sessions/{session_id}/messages",
    response={
        200: ChatMessageHistoryResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
    },
)
def get_chat_messages(request, session_id: int):
    session = ChatSessionService().get_user_session(request.user, session_id=session_id)
    if session is None:
        return 404, {"detail": "Chat session not found."}

    messages = ChatMessageService().list_messages(session)
    return ChatMessageHistoryResponseSchema(
        session=_serialize_session(session),
        messages=[_serialize_message(message) for message in messages],
    )


@router.post(
    "chat/sessions/{session_id}/messages",
    response={
        202: ChatSubmitAcceptedResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
        429: ErrorResponseSchema,
    },
)
def post_chat_message(request, session_id: int, payload: ChatSubmitMessageRequestSchema):
    session_service = ChatSessionService()
    session = session_service.get_user_session(request.user, session_id=session_id)
    if session is None:
        return 404, {"detail": "Chat session not found."}

    try:
        ChatMessageCreditService().consume_credit(request.user)
    except ChatMessageCreditLimitExceededError as exc:
        return 429, {"detail": str(exc)}

    message_service = ChatMessageService()
    user_message = message_service.create_user_message(session, content=payload.content.strip())
    session_service.assign_title_from_message(session, message_text=payload.content)
    turn = ChatTurnService().create_turn(session=session, user_message=user_message)
    ChatTurnTriggerService().request_turn_processing(turn=turn)
    return 202, ChatSubmitAcceptedResponseSchema(
        user_message=_serialize_message(user_message),
        turn=_serialize_turn(turn),
    )


@router.get(
    "chat/sessions/{session_id}/turns/{turn_id}",
    response={
        200: ChatTurnStatusResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
    },
)
def get_chat_turn_status(request, session_id: int, turn_id: int):
    session = ChatSessionService().get_user_session(request.user, session_id=session_id)
    if session is None:
        return 404, {"detail": "Chat session not found."}

    turn = ChatTurnService().get_user_turn(request.user, session_id=session_id, turn_id=turn_id)
    if turn is None:
        return 404, {"detail": "Chat turn not found."}

    return ChatTurnStatusResponseSchema(
        turn=_serialize_turn(turn),
        assistant_message=(
            _serialize_message(turn.assistant_message) if turn.assistant_message else None
        ),
    )


@router.get(
    "chat/sessions/{session_id}/proposals/{proposal_id}",
    response={
        200: ChatActionProposalResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
    },
)
def get_action_proposal(request, session_id: int, proposal_id: str):
    try:
        proposal = ChatActionProposalService().get_user_proposal(
            request.user,
            session_id=session_id,
            proposal_id=proposal_id,
        )
    except ActionProposalNotFoundError as exc:
        return 404, {"detail": str(exc)}

    return _serialize_proposal(proposal)


@router.post(
    "chat/sessions/{session_id}/proposals/{proposal_id}/approve",
    response={
        200: ChatActionProposalResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
        409: ErrorResponseSchema,
    },
)
def approve_action_proposal(request, session_id: int, proposal_id: str):
    try:
        proposal = ChatActionProposalService().approve_proposal(
            request.user,
            session_id=session_id,
            proposal_id=proposal_id,
        )
    except ActionProposalNotFoundError as exc:
        return 404, {"detail": str(exc)}
    except (ActionProposalConflictError, ActionProposalPolicyError) as exc:
        return 409, {"detail": str(exc)}

    return _serialize_proposal(proposal)


@router.post(
    "chat/sessions/{session_id}/proposals/{proposal_id}/reject",
    response={
        200: ChatActionProposalResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
        409: ErrorResponseSchema,
    },
)
def reject_action_proposal(request, session_id: int, proposal_id: str):
    try:
        proposal = ChatActionProposalService().reject_proposal(
            request.user,
            session_id=session_id,
            proposal_id=proposal_id,
        )
    except ActionProposalNotFoundError as exc:
        return 404, {"detail": str(exc)}
    except ActionProposalConflictError as exc:
        return 409, {"detail": str(exc)}

    return _serialize_proposal(proposal)
