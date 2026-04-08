from ninja import Schema


class EventResponseSchema(Schema):
    id: int
    google_event_id: str
    title: str
    description: str
    start_time: str
    end_time: str
    timezone: str
    location: str
    status: str
    attendees: list[dict]
    organizer_email: str
    is_all_day: bool
