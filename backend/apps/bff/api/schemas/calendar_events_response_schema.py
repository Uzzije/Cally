from ninja import Schema

from apps.bff.api.schemas.calendar_response_schema import CalendarResponseSchema
from apps.bff.api.schemas.event_response_schema import EventResponseSchema


class CalendarEventsResponseSchema(Schema):
    calendar: CalendarResponseSchema | None = None
    events: list[EventResponseSchema]
