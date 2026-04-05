import logging

from ninja import Router

from apps.bff.api.schemas.chat_message_history_response_schema import ChatMessageHistoryResponseSchema
from apps.bff.api.schemas.chat_message_response_schema import ChatMessageResponseSchema
from apps.bff.api.schemas.chat_session_response_schema import ChatSessionResponseSchema
from apps.bff.api.schemas.chat_sessions_response_schema import ChatSessionsResponseSchema
from apps.bff.api.schemas.chat_submit_message_request_schema import ChatSubmitMessageRequestSchema
from apps.bff.api.schemas.chat_submit_message_response_schema import ChatSubmitMessageResponseSchema
from apps.bff.api.schemas.error_response_schema import ErrorResponseSchema
from apps.chat.services.chat_assistant_turn_service import ChatAssistantTurnService
from apps.chat.services.chat_message_service import ChatMessageService
from apps.chat.services.chat_session_service import ChatSessionService
from apps.core.exceptions import AppConfigurationError


logger = logging.getLogger(__name__)

router = Router(tags=["chat"])


def _require_authenticated_user(request):
    if request.user.is_authenticated:
        return None

    return 401, {"detail": "Authentication credentials were not provided."}


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


@router.get(
    "chat/sessions",
    response={200: ChatSessionsResponseSchema, 401: ErrorResponseSchema},
)
def list_chat_sessions(request):
    auth_error = _require_authenticated_user(request)
    if auth_error:
        return auth_error

    sessions = ChatSessionService().list_sessions(request.user)
    return ChatSessionsResponseSchema(
        sessions=[_serialize_session(session) for session in sessions],
    )


@router.post(
    "chat/sessions",
    response={200: ChatSessionResponseSchema, 401: ErrorResponseSchema},
)
def create_chat_session(request):
    auth_error = _require_authenticated_user(request)
    if auth_error:
        return auth_error

    session = ChatSessionService().create_session(request.user)
    return _serialize_session(session)


@router.get(
    "chat/sessions/{session_id}/messages",
    response={200: ChatMessageHistoryResponseSchema, 401: ErrorResponseSchema, 404: ErrorResponseSchema},
)
def get_chat_messages(request, session_id: int):
    auth_error = _require_authenticated_user(request)
    if auth_error:
        return auth_error

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
        200: ChatSubmitMessageResponseSchema,
        401: ErrorResponseSchema,
        404: ErrorResponseSchema,
        503: ErrorResponseSchema,
    },
)
def post_chat_message(request, session_id: int, payload: ChatSubmitMessageRequestSchema):
    auth_error = _require_authenticated_user(request)
    if auth_error:
        return auth_error

    session_service = ChatSessionService()
    session = session_service.get_user_session(request.user, session_id=session_id)
    if session is None:
        return 404, {"detail": "Chat session not found."}

    message_service = ChatMessageService()
    user_message = message_service.create_user_message(session, content=payload.content.strip())
    session_service.assign_title_from_message(session, message_text=payload.content)

    try:
        assistant_turn = ChatAssistantTurnService().generate_response(
            session=session,
            user_prompt=payload.content,
        )
    except AppConfigurationError:
        logger.exception(
            "chat.assistant.turn.configuration_error session_id=%s user_id=%s",
            session.id,
            request.user.id,
        )
        return 503, {"detail": "Chat assistant is not configured yet."}
    except Exception:  # noqa: BLE001
        logger.exception(
            "chat.assistant.turn.failed session_id=%s user_id=%s",
            session.id,
            request.user.id,
        )
        return 503, {"detail": "Unable to generate an assistant response right now."}

    assistant_message = message_service.create_assistant_message(
        session,
        content_blocks=ChatAssistantTurnService().build_content_blocks(assistant_turn),
        tool_calls=assistant_turn.tool_calls,
    )
    return ChatSubmitMessageResponseSchema(
        user_message=_serialize_message(user_message),
        assistant_message=_serialize_message(assistant_message),
    )

