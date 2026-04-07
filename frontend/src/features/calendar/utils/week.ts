const DAY_MS = 24 * 60 * 60 * 1000
const WEEK_MS = 7 * DAY_MS

export function getStartOfWeek(date: Date) {
  const copy = new Date(date)
  const day = copy.getDay()
  const diff = day === 0 ? -6 : 1 - day
  copy.setHours(0, 0, 0, 0)
  copy.setDate(copy.getDate() + diff)
  return copy
}

export function getPreviousWeekStart(date: Date) {
  return new Date(date.getTime() - WEEK_MS)
}

export function getNextWeekStart(date: Date) {
  return new Date(date.getTime() + WEEK_MS)
}

export function buildWeekDays(weekStart: Date) {
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(weekStart.getTime() + (index * DAY_MS))
    return {
      key: date.toISOString(),
      date,
      dayLabel: date.toLocaleDateString('en-US', { weekday: 'short' }),
      dateLabel: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    }
  })
}

export function formatWeekRange(weekStart: Date) {
  const weekEnd = new Date(weekStart.getTime() + (6 * DAY_MS))
  const startLabel = weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  const endLabel = weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return `${startLabel} – ${endLabel}`
}

export function buildWeekOptions(
  visibleWeekStart: Date,
  { weeksBefore = 8, weeksAfter = 8 }: { weeksBefore?: number; weeksAfter?: number } = {},
) {
  return Array.from({ length: weeksBefore + weeksAfter + 1 }, (_, index) => {
    const offset = index - weeksBefore
    const weekStart = new Date(visibleWeekStart.getTime() + (offset * WEEK_MS))
    return {
      value: weekStart.toISOString(),
      label: formatWeekRange(weekStart),
      weekStart,
    }
  })
}

export function toApiDateRange(weekStart: Date) {
  const start = new Date(weekStart)
  const end = new Date(weekStart.getTime() + (7 * DAY_MS))
  return {
    start: start.toISOString(),
    end: end.toISOString(),
  }
}

function formatDateKey(value: string | Date, timeZone: string) {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone,
  })

  return formatter.format(new Date(value))
}

export function isSameCalendarDay(left: string, right: Date, timeZone: string) {
  return formatDateKey(left, timeZone || 'UTC') === formatDateKey(right, timeZone || 'UTC')
}

export function formatEventTimeRange(
  startTime: string,
  endTime: string,
  isAllDay: boolean,
  timeZone: string,
) {
  if (isAllDay) {
    return 'All day'
  }

  const start = new Date(startTime)
  const end = new Date(endTime)
  const formatter = new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: timeZone || 'UTC',
  })

  return `${formatter.format(start)} - ${formatter.format(end)}`
}
