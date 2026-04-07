import type { SettingsFieldErrors, UserPreferences } from '../types'
import type { TempBlockedTimeEntry } from '../types'


const backendBaseUrl =
  import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000'

export class SettingsClientError extends Error {
  fieldErrors: SettingsFieldErrors

  constructor(message: string, fieldErrors: SettingsFieldErrors = {}) {
    super(message)
    this.name = 'SettingsClientError'
    this.fieldErrors = fieldErrors
  }
}

async function handleJsonResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  const payload = (await response.json().catch(() => null)) as
    | { detail?: string; errors?: SettingsFieldErrors }
    | null

  if (!response.ok) {
    throw new SettingsClientError(payload?.detail ?? fallbackMessage, payload?.errors ?? {})
  }

  return payload as T
}

export async function fetchPreferences(): Promise<UserPreferences> {
  const response = await fetch(`${backendBaseUrl}/api/v1/settings/preferences`, {
    credentials: 'include',
  })

  return handleJsonResponse<UserPreferences>(response, 'Unable to fetch preferences')
}

export async function updatePreferences(
  preferences: UserPreferences,
  csrfToken: string,
): Promise<UserPreferences> {
  const response = await fetch(`${backendBaseUrl}/api/v1/settings/preferences`, {
    method: 'PUT',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify(preferences),
  })

  return handleJsonResponse<UserPreferences>(response, 'Unable to update preferences')
}

export async function fetchTempBlockedTimes(): Promise<{ entries: TempBlockedTimeEntry[] }> {
  const response = await fetch(`${backendBaseUrl}/api/v1/settings/temp-blocked-times`, {
    credentials: 'include',
  })

  return handleJsonResponse<{ entries: TempBlockedTimeEntry[] }>(
    response,
    'Unable to fetch temporary blocked times',
  )
}

export async function createTempBlockedTimes(
  payload: {
    timezone: string
    entries: Array<Pick<TempBlockedTimeEntry, 'label' | 'date' | 'start' | 'end' | 'source'>>
  },
  csrfToken: string,
): Promise<{ entries: TempBlockedTimeEntry[] }> {
  const response = await fetch(`${backendBaseUrl}/api/v1/settings/temp-blocked-times`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify(payload),
  })

  return handleJsonResponse<{ entries: TempBlockedTimeEntry[] }>(
    response,
    'Unable to create temporary blocked times',
  )
}

export async function deleteTempBlockedTime(
  entryId: string,
  csrfToken: string,
): Promise<{ entries: TempBlockedTimeEntry[] }> {
  const response = await fetch(`${backendBaseUrl}/api/v1/settings/temp-blocked-times/${entryId}`, {
    method: 'DELETE',
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  return handleJsonResponse<{ entries: TempBlockedTimeEntry[] }>(
    response,
    'Unable to delete temporary blocked time',
  )
}

export async function clearTempBlockedTimes(
  csrfToken: string,
): Promise<{ entries: TempBlockedTimeEntry[] }> {
  const response = await fetch(`${backendBaseUrl}/api/v1/settings/temp-blocked-times`, {
    method: 'DELETE',
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  return handleJsonResponse<{ entries: TempBlockedTimeEntry[] }>(
    response,
    'Unable to clear temporary blocked times',
  )
}

export async function deleteAccount(csrfToken: string): Promise<{ success: boolean }> {
  const response = await fetch(`${backendBaseUrl}/api/v1/auth/delete-account`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  return handleJsonResponse<{ success: boolean }>(response, 'Unable to delete account')
}
