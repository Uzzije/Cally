import type { BlockedTimeEntry, TempBlockedTimeEntry, WeekdayCode } from '../../settings/types'


type WeekDay = {
  key: string
  date: Date
  dayLabel: string
  dateLabel: string
}

export type BlockedTimeSegment = {
  dayKey: string
  entryId: string
  key: string
  label: string
  top: number
  height: number
}

const DAY_CODE_BY_WEEKDAY: Record<string, string> = {
  mon: 'mon',
  tue: 'tue',
  wed: 'wed',
  thu: 'thu',
  fri: 'fri',
  sat: 'sat',
  sun: 'sun',
}

function getWeekdayCode(date: Date, timeZone: string): WeekdayCode | undefined {
  const weekday = new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    timeZone,
  })
    .format(date)
    .toLowerCase()

  return DAY_CODE_BY_WEEKDAY[weekday] as WeekdayCode | undefined
}

function getMinutesFromTime(timeValue: string) {
  const [hour, minute] = timeValue.split(':').map(Number)
  return ((Number.isNaN(hour) ? 0 : hour) * 60) + (Number.isNaN(minute) ? 0 : minute)
}

function getIsoDateInTimeZone(date: Date, timeZone: string) {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })

  return formatter.format(date)
}

export function expandBlockedTimesForWeek({
  blockedTimes,
  tempBlockedTimes,
  weekDays,
  timeZone,
}: {
  blockedTimes: BlockedTimeEntry[]
  tempBlockedTimes?: TempBlockedTimeEntry[]
  weekDays: WeekDay[]
  timeZone: string
}): BlockedTimeSegment[] {
  return weekDays.flatMap((day) => {
    const weekdayCode = getWeekdayCode(day.date, timeZone)
    if (!weekdayCode) {
      return []
    }

    const recurringSegments = blockedTimes
      .filter((entry) => entry.days.includes(weekdayCode))
      .map((entry) => {
        const startMinutes = getMinutesFromTime(entry.start)
        const endMinutes = getMinutesFromTime(entry.end)
        const durationMinutes = Math.max(endMinutes - startMinutes, 0)

        return {
          dayKey: day.key,
          entryId: entry.id,
          key: `${day.key}-${entry.id}`,
          label: entry.label,
          top: (startMinutes / (24 * 60)) * 100,
          height: Math.max((durationMinutes / (24 * 60)) * 100, 3.5),
        }
      })

    const dayIsoDate = getIsoDateInTimeZone(day.date, timeZone)
    const temporarySegments = (tempBlockedTimes ?? [])
      .filter((entry) => entry.date === dayIsoDate)
      .map((entry) => {
        const startMinutes = getMinutesFromTime(entry.start)
        const endMinutes = getMinutesFromTime(entry.end)
        const durationMinutes = Math.max(endMinutes - startMinutes, 0)

        return {
          dayKey: day.key,
          entryId: entry.id,
          key: `${day.key}-${entry.id}`,
          label: entry.label,
          top: (startMinutes / (24 * 60)) * 100,
          height: Math.max((durationMinutes / (24 * 60)) * 100, 3.5),
        }
      })

    return [...recurringSegments, ...temporarySegments]
  })
}
