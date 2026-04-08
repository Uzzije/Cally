from ninja import Schema


class SavedInsightPolicySchema(Schema):
    max_saved_insights: int
    current_count: int
    replaces_on_save: bool
    upgrade_message: str
