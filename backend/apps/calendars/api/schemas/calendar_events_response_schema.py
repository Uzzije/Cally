from ninja import Schema

from apps.calendars.api.schemas.calendar_response_schema import CalendarResponseSchema
from apps.calendars.api.schemas.event_response_schema import EventResponseSchema


class CalendarEventsResponseSchema(Schema):
    calendar: CalendarResponseSchema | None = None
    events: list[EventResponseSchema]

