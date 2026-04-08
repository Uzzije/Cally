import type { CalendarEvent } from '../types'
import { parseLocationLink, toDisplayText } from '../utils/eventContent'
import { formatEventTimeRange } from '../utils/week'


export function EventDetailsPanel({
  event,
  timeZone,
}: {
  event: CalendarEvent | null
  timeZone: string
}) {
  const eventTitle = event ? toDisplayText(event.title) || 'Untitled event' : 'Choose an event'
  const location = parseLocationLink(event?.location)
  const description = event ? toDisplayText(event.description) : ''

  return (
    <aside className="paper-panel calendar-sidebar">
      <div className="card-heading">
        <p className="eyebrow">Event Details</p>
        <h2>{eventTitle}</h2>
      </div>

      {event ? (
        <dl className="details-grid calendar-detail-grid">
          <div>
            <dt>Time</dt>
            <dd>
              {formatEventTimeRange(
                event.start_time,
                event.end_time,
                event.is_all_day,
                timeZone,
              )}
            </dd>
          </div>
          <div>
            <dt>Location</dt>
            <dd>
              {location.href ? (
                <a
                  className="calendar-detail-link"
                  href={location.href}
                  rel="noreferrer"
                  target="_blank"
                  title={location.href}
                >
                  {location.text}
                </a>
              ) : (
                location.text
              )}
            </dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{toDisplayText(event.status) || 'Unknown'}</dd>
          </div>
          <div>
            <dt>Organizer</dt>
            <dd>{toDisplayText(event.organizer_email) || 'Not provided'}</dd>
          </div>
          <div className="calendar-detail-span">
            <dt>Description</dt>
            <dd className="calendar-description-text">
              {description || 'No description for this event.'}
            </dd>
          </div>
        </dl>
      ) : (
        <p>
          Select an event block from the weekly grid to inspect its title, time, and
          supporting metadata.
        </p>
      )}

    </aside>
  )
}
