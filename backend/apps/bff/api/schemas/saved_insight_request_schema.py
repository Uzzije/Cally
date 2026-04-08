from ninja import Schema


class SavedInsightRequestSchema(Schema):
    assistant_message_id: int
    block_index: int
