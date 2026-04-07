import type { EmailDraftBlock } from '../types'
import type { TempBlockedTimeEntry } from '../../settings/types'


const MONTH_INDEX_BY_SHORT_NAME: Record<string, number> = {
  jan: 0,
  feb: 1,
  mar: 2,
  apr: 3,
  may: 4,
  jun: 5,
  jul: 6,
  aug: 7,
  sep: 8,
  oct: 9,
  nov: 10,
  dec: 11,
}

const SUGGESTED_TIME_PATTERN =
  /^[•*-]\s*(?:[A-Za-z]{3},\s*)?([A-Za-z]{3})\s+(\d{1,2})\s+[—-]\s+(\d{1,2}):(\d{2})[–-](\d{1,2}):(\d{2})\s*(AM|PM)\b/i

function createTempBlockedTimeId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `temp-blocked-${crypto.randomUUID()}`
  }

  return `temp-blocked-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function padTimePart(value: number) {
  return `${value}`.padStart(2, '0')
}

function to24Hour(hour: number, meridiem: string) {
  const normalizedMeridiem = meridiem.toUpperCase()
  if (normalizedMeridiem === 'AM') {
    return hour === 12 ? 0 : hour
  }

  return hour === 12 ? 12 : hour + 12
}

function inferDate(monthShortName: string, day: number, now: Date) {
  const monthIndex = MONTH_INDEX_BY_SHORT_NAME[monthShortName.toLowerCase()]
  if (monthIndex === undefined) {
    return null
  }

  let year = now.getFullYear()
  let candidate = new Date(year, monthIndex, day)
  if (candidate.getTime() < now.getTime() - (24 * 60 * 60 * 1000)) {
    candidate = new Date(year + 1, monthIndex, day)
    year += 1
  }

  return {
    year,
    monthIndex,
    day,
    isoDate: `${year}-${padTimePart(monthIndex + 1)}-${padTimePart(day)}`,
  }
}

export function buildEmailDraftClipboardText(block: EmailDraftBlock) {
  const lines = [
    `To: ${block.to.join(', ')}`,
  ]

  if (block.cc && block.cc.length > 0) {
    lines.push(`Cc: ${block.cc.join(', ')}`)
  }

  lines.push(`Subject: ${block.subject}`)
  lines.push('')
  lines.push(block.body)

  return lines.join('\n')
}

export function extractTempBlockedTimesFromEmailDraft(
  block: EmailDraftBlock,
  now: Date = new Date(),
): TempBlockedTimeEntry[] {
  return block.body
    .split('\n')
    .map((line) => line.trim())
    .flatMap((line) => {
      const match = line.match(SUGGESTED_TIME_PATTERN)
      if (!match) {
        return []
      }

      const [, monthShortName, dayValue, startHourValue, startMinuteValue, endHourValue, endMinuteValue, meridiem] =
        match
      const inferredDate = inferDate(monthShortName, Number(dayValue), now)
      if (!inferredDate) {
        return []
      }

      const startHour = to24Hour(Number(startHourValue), meridiem)
      const endHour = to24Hour(Number(endHourValue), meridiem)

      return [
        {
          id: createTempBlockedTimeId(),
          label: `Hold for ${block.subject}`,
          date: inferredDate.isoDate,
          start: `${padTimePart(startHour)}:${startMinuteValue}`,
          end: `${padTimePart(endHour)}:${endMinuteValue}`,
          source: 'email_draft' as const,
          created_at: now.toISOString(),
        },
      ]
    })
}
