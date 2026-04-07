from ninja import Schema

from apps.preferences.api.schemas.blocked_time_schema import BlockedTimeSchema


class UserPreferencesRequestSchema(Schema):
    execution_mode: str
    display_timezone: str | None = None
    blocked_times: list[BlockedTimeSchema]
