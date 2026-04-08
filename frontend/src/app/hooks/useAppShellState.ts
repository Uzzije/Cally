import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

import {
  clearTempBlockedTimes,
  createTempBlockedTimes,
  deleteTempBlockedTime,
  fetchTempBlockedTimes,
} from '../../features/settings/api/settingsClient'
import type { TempBlockedTimeEntry } from '../../features/settings/types'
import { fetchChatCredits } from '../../features/chat/api/chatClient'
import type { MessageCreditStatus } from '../../features/chat/types'
import { ensureCsrfCookie, fetchSession } from '../../features/auth/api/authClient'
import type { AuthSession } from '../../features/auth/types'
import { getCookie } from '../../shared/lib/cookies'


type TempBlockedTimesSaveResult = {
  createdCount: number
  updatedCount: number
}

type AppShellState = {
  hasError: boolean
  isLoading: boolean
  messageCredits: MessageCreditStatus | null
  refreshMessageCredits: () => Promise<void>
  clearAllTempBlockedTimes: () => Promise<void>
  addTempBlockedTimes: (entries: TempBlockedTimeEntry[]) => Promise<TempBlockedTimesSaveResult>
  loadSession: () => Promise<void>
  removeTempBlockedTime: (entryId: string) => Promise<void>
  session: AuthSession | null
  tempBlockedTimes: TempBlockedTimeEntry[]
}

export function useAppShellState(): AppShellState {
  const location = useLocation()
  const [session, setSession] = useState<AuthSession | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [messageCredits, setMessageCredits] = useState<MessageCreditStatus | null>(null)
  const [tempBlockedTimes, setTempBlockedTimes] = useState<TempBlockedTimeEntry[]>([])

  const refreshTempBlockedTimes = useCallback(async () => {
    const response = await fetchTempBlockedTimes()
    setTempBlockedTimes(response.entries)
  }, [])

  const addTempBlockedTimes = useCallback(async (entries: TempBlockedTimeEntry[]) => {
    const currentEntries = tempBlockedTimes
    const timeZone =
      entries[0]?.timezone ||
      Intl.DateTimeFormat().resolvedOptions().timeZone ||
      'UTC'
    const response = await createTempBlockedTimes(
      {
        timezone: timeZone,
        entries: entries.map((entry) => ({
          label: entry.label,
          date: entry.date,
          start: entry.start,
          end: entry.end,
          source: entry.source,
        })),
      },
      getCookie('csrftoken'),
    )

    setTempBlockedTimes((current) => {
      const returnedIds = new Set(response.entries.map((entry) => entry.id))
      return [...response.entries, ...current.filter((entry) => !returnedIds.has(entry.id))]
    })

    const matchedEntries = entries.filter((entry) =>
      currentEntries.some(
        (current) =>
          current.date === entry.date &&
          current.start === entry.start &&
          current.end === entry.end &&
          (current.timezone || timeZone) === (entry.timezone || timeZone),
      ),
    )

    return {
      createdCount: entries.length - matchedEntries.length,
      updatedCount: matchedEntries.length,
    }
  }, [tempBlockedTimes])

  const removeTempBlockedTime = useCallback(async (entryId: string) => {
    const response = await deleteTempBlockedTime(entryId, getCookie('csrftoken'))
    setTempBlockedTimes(response.entries)
  }, [])

  const clearAllTempBlockedTimes = useCallback(async () => {
    const response = await clearTempBlockedTimes(getCookie('csrftoken'))
    setTempBlockedTimes(response.entries)
  }, [])

  const refreshMessageCredits = useCallback(async () => {
    const response = await fetchChatCredits()
    setMessageCredits(response)
  }, [])

  const loadSession = useCallback(async () => {
    setHasError(false)
    setIsLoading(true)

    try {
      await ensureCsrfCookie()
      const nextSession = await fetchSession()
      setSession(nextSession)

      if (nextSession.authenticated) {
        try {
          await refreshTempBlockedTimes()
        } catch {
          setTempBlockedTimes([])
        }

        try {
          await refreshMessageCredits()
        } catch {
          setMessageCredits(null)
        }

        return
      }

      setTempBlockedTimes([])
      setMessageCredits(null)
    } catch {
      setHasError(true)
    } finally {
      setIsLoading(false)
    }
  }, [refreshMessageCredits, refreshTempBlockedTimes])

  useEffect(() => {
    void loadSession()
  }, [location.pathname, loadSession])

  return {
    addTempBlockedTimes,
    clearAllTempBlockedTimes,
    hasError,
    isLoading,
    loadSession,
    messageCredits,
    refreshMessageCredits,
    removeTempBlockedTime,
    session,
    tempBlockedTimes,
  }
}
