from ninja import Schema

from apps.bff.api.schemas.chat_message_response_schema import ChatMessageResponseSchema
from apps.bff.api.schemas.chat_turn_response_schema import ChatTurnResponseSchema


class ChatTurnStatusResponseSchema(Schema):
    turn: ChatTurnResponseSchema
    assistant_message: ChatMessageResponseSchema | None = None
