import type { CalendarResponse, CalendarSyncStatus } from '../types'


const backendBaseUrl =
  import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000'

type CalendarRange = {
  start: string
  end: string
}

async function handleJsonResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    throw new Error(fallbackMessage)
  }

  return response.json() as Promise<T>
}

export async function fetchCalendarEvents(range: CalendarRange): Promise<CalendarResponse> {
  const search = new URLSearchParams(range)
  const response = await fetch(`${backendBaseUrl}/api/v1/calendar/events?${search.toString()}`, {
    credentials: 'include',
  })

  return handleJsonResponse<CalendarResponse>(response, 'Unable to fetch calendar events')
}

export async function fetchCalendarSyncStatus(): Promise<CalendarSyncStatus> {
  const response = await fetch(`${backendBaseUrl}/api/v1/calendar/sync-status`, {
    credentials: 'include',
  })

  return handleJsonResponse<CalendarSyncStatus>(response, 'Unable to fetch sync status')
}

export async function triggerCalendarSync(csrfToken: string) {
  const response = await fetch(`${backendBaseUrl}/api/v1/calendar/sync`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  return handleJsonResponse(response, 'Unable to sync calendar')
}
