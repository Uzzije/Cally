from ninja import Schema

from apps.bff.api.schemas.chat_message_response_schema import ChatMessageResponseSchema
from apps.bff.api.schemas.chat_session_response_schema import ChatSessionResponseSchema


class ChatMessageHistoryResponseSchema(Schema):
    session: ChatSessionResponseSchema
    messages: list[ChatMessageResponseSchema]

