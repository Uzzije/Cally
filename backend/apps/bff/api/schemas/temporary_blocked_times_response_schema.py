from ninja import Schema

from apps.bff.api.schemas.temporary_blocked_time_schema import TemporaryBlockedTimeSchema


class TemporaryBlockedTimesResponseSchema(Schema):
    entries: list[TemporaryBlockedTimeSchema]
