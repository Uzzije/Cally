const FALLBACK_TIME_ZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Asia/Tokyo',
  'Australia/Sydney',
]

export function getDisplayTimezoneOptions(currentValue?: string | null) {
  const browserTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
  const intlWithSupportedValues = Intl as typeof Intl & {
    supportedValuesOf?: (key: 'timeZone') => string[]
  }
  const supportedTimeZones =
    typeof intlWithSupportedValues.supportedValuesOf === 'function'
      ? intlWithSupportedValues.supportedValuesOf('timeZone')
      : FALLBACK_TIME_ZONES

  return Array.from(
    new Set(
      ['', browserTimeZone, ...(currentValue ? [currentValue] : []), ...supportedTimeZones],
    ),
  )
}
