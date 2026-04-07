from ninja import Schema

from apps.bff.api.schemas.chat_message_response_schema import ChatMessageResponseSchema
from apps.bff.api.schemas.chat_turn_response_schema import ChatTurnResponseSchema


class ChatSubmitAcceptedResponseSchema(Schema):
    user_message: ChatMessageResponseSchema
    turn: ChatTurnResponseSchema
