export type CalendarEvent = {
  id: number
  google_event_id: string
  title: string
  description: string
  start_time: string
  end_time: string
  timezone: string
  location: string
  status: string
  attendees: Array<{ email?: string }>
  organizer_email: string
  is_all_day: boolean
}

export type CalendarResponse = {
  calendar: {
    id: number
    name: string
    is_primary: boolean
    last_synced_at: string | null
  } | null
  events: CalendarEvent[]
}

export type CalendarSyncStatus = {
  has_calendar: boolean
  sync_state: string
  last_synced_at: string | null
  is_stale: boolean
}

export type CalendarApiErrorCode = 'google_reauth_required'

export type CalendarApiErrorPayload = {
  detail: string
  code?: CalendarApiErrorCode
}
