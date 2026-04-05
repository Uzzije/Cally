import { useEffect, useRef } from 'react'

import type { CalendarEvent } from '../types'
import { getEventBlockStyle } from '../utils/layout'
import { formatEventTimeRange, isSameCalendarDay } from '../utils/week'


type WeekDay = {
  key: string
  date: Date
  dayLabel: string
  dateLabel: string
}

type CalendarWeekViewProps = {
  events: CalendarEvent[]
  isLoading: boolean
  selectedEventId: number | null
  scrollTargetTop: number
  weekDays: WeekDay[]
  onSelectEvent: (eventId: number) => void
}

const HOURS = Array.from({ length: 24 }, (_, hour) => hour)

function formatHourLabel(hour: number) {
  const date = new Date(Date.UTC(2026, 3, 6, hour))
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    timeZone: 'UTC',
  }).format(date)
}

export function CalendarWeekView({
  events,
  isLoading,
  selectedEventId,
  scrollTargetTop,
  weekDays,
  onSelectEvent,
}: CalendarWeekViewProps) {
  const viewportRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!viewportRef.current || isLoading) {
      return
    }

    if (typeof viewportRef.current.scrollTo === 'function') {
      viewportRef.current.scrollTo({
        top: scrollTargetTop,
        behavior: 'smooth',
      })
      return
    }

    viewportRef.current.scrollTop = scrollTargetTop
  }, [isLoading, scrollTargetTop])

  return (
    <div className="calendar-grid-viewport" ref={viewportRef}>
      <div className="calendar-grid-shell">
        <div className="calendar-time-column" aria-hidden="true">
          <div className="calendar-day-header-spacer" />
          <div className="calendar-time-scale">
            {HOURS.map((hour) => (
              <div className="calendar-time-label" key={hour}>
                {formatHourLabel(hour)}
              </div>
            ))}
          </div>
        </div>

        <div className="calendar-day-columns">
          {weekDays.map((day) => {
            const dayEvents = events.filter((event) =>
              isSameCalendarDay(event.start_time, day.date, event.timezone),
            )

            return (
              <section className="calendar-day-column" key={day.key}>
                <header className="calendar-day-header">
                  <p>{day.dayLabel}</p>
                  <span>{day.dateLabel}</span>
                </header>
                <div className="calendar-day-body">
                  {HOURS.map((hour) => (
                    <div className="calendar-hour-line" key={`${day.key}-${hour}`} />
                  ))}

                  {isLoading ? (
                    <div className="calendar-loading-state">Loading week…</div>
                  ) : null}

                  {dayEvents.map((event) => {
                    const style = getEventBlockStyle({
                      startTime: event.start_time,
                      endTime: event.end_time,
                      timeZone: event.timezone,
                    })

                    return (
                      <button
                        className={`calendar-event-card${selectedEventId === event.id ? ' is-selected' : ''}`}
                        key={event.id}
                        style={{
                          top: `${style.top}%`,
                          height: `${style.height}%`,
                        }}
                        onClick={() => onSelectEvent(event.id)}
                      >
                        <strong>{event.title}</strong>
                        <span>
                          {formatEventTimeRange(
                            event.start_time,
                            event.end_time,
                            event.is_all_day,
                            event.timezone,
                          )}
                        </span>
                      </button>
                    )
                  })}
                </div>
              </section>
            )
          })}
        </div>
      </div>
    </div>
  )
}
