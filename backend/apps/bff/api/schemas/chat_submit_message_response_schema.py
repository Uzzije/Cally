from ninja import Schema

from apps.bff.api.schemas.chat_message_response_schema import ChatMessageResponseSchema


class ChatSubmitMessageResponseSchema(Schema):
    user_message: ChatMessageResponseSchema
    assistant_message: ChatMessageResponseSchema

