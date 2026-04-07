import { getCookie } from '../../../shared/lib/cookies'
import type { AuthSession } from '../types'


const backendBaseUrl =
  import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000'

export function getGoogleLoginUrl() {
  return `${backendBaseUrl}/accounts/google/login/?process=login`
}

export async function fetchSession(): Promise<AuthSession> {
  const response = await fetch(`${backendBaseUrl}/api/v1/auth/me`, {
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error('Unable to fetch session')
  }

  return response.json()
}

export async function ensureCsrfCookie() {
  await fetch(`${backendBaseUrl}/api/v1/auth/csrf`, {
    credentials: 'include',
  })
}

export async function logoutUser() {
  const response = await fetch(`${backendBaseUrl}/api/v1/auth/logout`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'X-CSRFToken': getCookie('csrftoken'),
    },
  })

  if (!response.ok) {
    throw new Error('Unable to sign out')
  }
}
