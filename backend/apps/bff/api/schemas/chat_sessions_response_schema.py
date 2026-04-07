from ninja import Schema

from apps.bff.api.schemas.chat_session_response_schema import ChatSessionResponseSchema


class ChatSessionsResponseSchema(Schema):
    sessions: list[ChatSessionResponseSchema]
