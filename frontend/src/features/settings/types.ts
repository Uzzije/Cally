export type ExecutionMode = 'draft_only' | 'confirm'

export type WeekdayCode =
  | 'mon'
  | 'tue'
  | 'wed'
  | 'thu'
  | 'fri'
  | 'sat'
  | 'sun'

export type BlockedTimeEntry = {
  id: string
  label: string
  days: WeekdayCode[]
  start: string
  end: string
}

export type TempBlockedTimeEntry = {
  id: string
  label: string
  date: string
  start: string
  end: string
  timezone?: string
  source: 'email_draft'
  created_at: string
  expires_at?: string
}

export type UserPreferences = {
  execution_mode: ExecutionMode
  display_timezone: string | null
  blocked_times: BlockedTimeEntry[]
}

export type SettingsFieldErrors = Record<string, string[]>
