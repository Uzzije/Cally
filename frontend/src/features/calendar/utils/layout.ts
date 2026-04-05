import type { CalendarEvent } from '../types'


export const CALENDAR_TOTAL_MINUTES = 24 * 60
export const CALENDAR_HOUR_ROW_HEIGHT = 42

function getZonedHourAndMinute(isoString: string, timeZone: string) {
  const formatter = new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone,
  })
  const parts = formatter.formatToParts(new Date(isoString))
  const hour = Number(parts.find((part) => part.type === 'hour')?.value ?? '0')
  const minute = Number(parts.find((part) => part.type === 'minute')?.value ?? '0')

  return { hour, minute }
}

export function getEventBlockStyle({
  startTime,
  endTime,
  timeZone,
}: {
  startTime: string
  endTime: string
  timeZone: string
}) {
  const start = getZonedHourAndMinute(startTime, timeZone || 'UTC')
  const end = getZonedHourAndMinute(endTime, timeZone || 'UTC')
  const startMinutes = (start.hour * 60) + start.minute
  const endMinutes = (end.hour * 60) + end.minute

  return {
    top: (startMinutes / CALENDAR_TOTAL_MINUTES) * 100,
    height: Math.max(((endMinutes - startMinutes) / CALENDAR_TOTAL_MINUTES) * 100, 3.5),
  }
}

export function getEventStartMinutes(event: CalendarEvent) {
  const start = getZonedHourAndMinute(event.start_time, event.timezone || 'UTC')
  return (start.hour * 60) + start.minute
}

export function getInitialCalendarScrollTop(events: CalendarEvent[]) {
  if (events.length === 0) {
    return 0
  }

  const earliestStartMinutes = Math.min(...events.map(getEventStartMinutes))
  const scrollTargetMinutes = Math.max(earliestStartMinutes - 60, 0)
  return Math.floor((scrollTargetMinutes / 60) * CALENDAR_HOUR_ROW_HEIGHT)
}
