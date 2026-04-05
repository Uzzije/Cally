import { startTransition, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { CalendarWeekView } from './features/calendar/components/CalendarWeekView'
import { EventDetailsPanel } from './features/calendar/components/EventDetailsPanel'
import { SyncStatusIndicator } from './features/calendar/components/SyncStatusIndicator'
import {
  fetchCalendarEvents,
  fetchCalendarSyncStatus,
  triggerCalendarSync,
} from './features/calendar/api/calendarClient'
import type { CalendarEvent, CalendarSyncStatus } from './features/calendar/types'
import { getInitialCalendarScrollTop } from './features/calendar/utils/layout'
import {
  buildWeekDays,
  formatWeekRange,
  getNextWeekStart,
  getPreviousWeekStart,
  getStartOfWeek,
  toApiDateRange,
} from './features/calendar/utils/week'
import {
  createChatSession,
  fetchChatMessages,
  fetchChatSessions,
  submitChatMessage,
} from './features/chat/api/chatClient'
import { ChatComposer } from './features/chat/components/ChatComposer'
import { ChatSessionSwitcher } from './features/chat/components/ChatSessionSwitcher'
import { ChatStatusLine } from './features/chat/components/ChatStatusLine'
import { MessageList } from './features/chat/components/MessageList'
import type { ChatMessage, ChatSessionSummary } from './features/chat/types'


type AuthUser = {
  id: number
  email: string
  display_name: string
  avatar_url: string | null
  has_google_account: boolean
  onboarding_completed: boolean
}

type AuthSession = {
  authenticated: boolean
  user: AuthUser | null
}

const backendBaseUrl =
  import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000'

function getCookie(name: string) {
  const cookies = document.cookie.split(';')
  for (const cookie of cookies) {
    const trimmedCookie = cookie.trim()
    if (trimmedCookie.startsWith(`${name}=`)) {
      return decodeURIComponent(trimmedCookie.substring(name.length + 1))
    }
  }
  return ''
}

async function fetchSession(): Promise<AuthSession> {
  const response = await fetch(`${backendBaseUrl}/api/v1/auth/me`, {
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error('Unable to fetch session')
  }

  return response.json()
}

async function ensureCsrfCookie() {
  await fetch(`${backendBaseUrl}/api/v1/auth/csrf`, {
    credentials: 'include',
  })
}

async function logoutUser() {
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

function LoadingScreen() {
  return (
    <main className="app-shell centered-shell">
      <section className="paper-panel status-panel">
        <p className="eyebrow">Cal Assistant</p>
        <h1>Checking your session</h1>
        <p>Preparing your workspace and connected account state.</p>
      </section>
    </main>
  )
}

function ErrorScreen({
  title,
  message,
  onRetry,
}: {
  title: string
  message: string
  onRetry: () => void
}) {
  return (
    <main className="app-shell centered-shell">
      <section className="paper-panel status-panel">
        <p className="eyebrow">Session Error</p>
        <h1>{title}</h1>
        <p>{message}</p>
        <button className="primary-button button-md" onClick={onRetry}>
          Try Again
        </button>
      </section>
    </main>
  )
}

function LoginPage() {
  const googleLoginUrl = `${backendBaseUrl}/accounts/google/login/?process=login`

  return (
    <main className="login-shell">
      <div className="login-atmosphere login-atmosphere-left" />
      <div className="login-atmosphere login-atmosphere-right" />

      <section className="login-stage">
        <div className="brand-stack">
          <div className="brand-mark" aria-hidden="true">
            <span className="brand-book">
              <span />
              <span />
            </span>
          </div>
          <p className="brand-name">Cal Assistant</p>
          <p className="brand-tagline">Calendar workspace</p>
        </div>

        <section className="login-card" aria-label="Sign in">
          <div className="login-copy">
            <h1>Welcome back</h1>
            <p>
              Sign in to access your calendar workspace and connected Google account.
            </p>
          </div>

          <a className="google-button button-lg" href={googleLoginUrl}>
            <span className="google-mark" aria-hidden="true">
              G
            </span>
            <span>Sign in with Google</span>
          </a>

          <div className="login-divider" />

          <div className="login-meta">
            <p>Google sign-in is required for secure calendar access.</p>
          </div>
        </section>

        <footer className="login-footer">
          <a href="mailto:support@calassistant.local">Privacy Policy</a>
          <a href="mailto:support@calassistant.local">Terms of Service</a>
          <a href="mailto:support@calassistant.local">Support</a>
        </footer>
      </section>
    </main>
  )
}

function AuthErrorPage() {
  return (
    <main className="workspace-page centered-shell">
      <section className="paper-panel status-panel">
        <p className="eyebrow">Authentication</p>
        <h1>We couldn&apos;t complete sign in</h1>
        <p>
          The Google login flow was interrupted or rejected. Return to the login
          screen and try again.
        </p>
        <a className="primary-link-button button-md" href="/">
          Return to login
        </a>
      </section>
    </main>
  )
}

function ChatWorkspace({
  csrfToken,
}: {
  csrfToken: string
}) {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([])
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [chatError, setChatError] = useState<string | null>(null)
  const [isSessionsLoading, setIsSessionsLoading] = useState(true)
  const [isMessagesLoading, setIsMessagesLoading] = useState(false)
  const [isCreatingSession, setIsCreatingSession] = useState(false)
  const [isSubmittingMessage, setIsSubmittingMessage] = useState(false)

  const refreshSessions = async (nextActiveSessionId?: number | null) => {
    const response = await fetchChatSessions()
    setSessions(response.sessions)
    if (response.sessions.length === 0) {
      startTransition(() => setActiveSessionId(null))
      return response.sessions
    }

    const targetSessionId =
      nextActiveSessionId ??
      (response.sessions.some((session) => session.id === activeSessionId)
        ? activeSessionId
        : response.sessions[0].id)

    startTransition(() => setActiveSessionId(targetSessionId))
    return response.sessions
  }

  const createAndSelectSession = async () => {
    setIsCreatingSession(true)
    try {
      const createdSession = await createChatSession(csrfToken)
      const nextSessions = await refreshSessions(createdSession.id)
      if (!nextSessions.some((session) => session.id === createdSession.id)) {
        setSessions((current) => [createdSession, ...current])
      }
      setMessages([])
      setChatError(null)
      return createdSession.id
    } finally {
      setIsCreatingSession(false)
    }
  }

  useEffect(() => {
    let cancelled = false

    const loadSessions = async () => {
      setIsSessionsLoading(true)
      setChatError(null)

      try {
        const response = await fetchChatSessions()
        if (cancelled) {
          return
        }

        setSessions(response.sessions)
        if (response.sessions.length === 0) {
          const createdSession = await createChatSession(csrfToken)
          if (cancelled) {
            return
          }
          setSessions([createdSession])
          startTransition(() => setActiveSessionId(createdSession.id))
        } else {
          startTransition(() => setActiveSessionId(response.sessions[0].id))
        }
      } catch {
        if (!cancelled) {
          setChatError('We could not load chat sessions right now.')
        }
      } finally {
        if (!cancelled) {
          setIsSessionsLoading(false)
        }
      }
    }

    void loadSessions()

    return () => {
      cancelled = true
    }
  }, [csrfToken])

  useEffect(() => {
    let cancelled = false

    const loadMessages = async () => {
      if (!activeSessionId) {
        setMessages([])
        setIsMessagesLoading(false)
        return
      }

      setIsMessagesLoading(true)
      setChatError(null)

      try {
        const response = await fetchChatMessages(activeSessionId)
        if (!cancelled) {
          setMessages(response.messages)
        }
      } catch {
        if (!cancelled) {
          setChatError('We could not load this conversation.')
        }
      } finally {
        if (!cancelled) {
          setIsMessagesLoading(false)
        }
      }
    }

    void loadMessages()

    return () => {
      cancelled = true
    }
  }, [activeSessionId])

  const handleCreateSession = async () => {
    setChatError(null)

    try {
      await createAndSelectSession()
    } catch {
      setChatError('We could not start a new conversation.')
    }
  }

  const handleSubmitMessage = async () => {
    const trimmedDraft = draft.trim()
    if (!trimmedDraft || isSubmittingMessage) {
      return
    }

    const createdAt = new Date().toISOString()
    const optimisticUserMessage: ChatMessage = {
      id: `pending-user-${createdAt}`,
      role: 'user',
      created_at: createdAt,
      content_blocks: [{ type: 'text', text: trimmedDraft }],
    }
    const pendingAssistantMessage: ChatMessage = {
      id: `pending-assistant-${createdAt}`,
      role: 'assistant',
      created_at: createdAt,
      pending: true,
      content_blocks: [{ type: 'status', text: 'Thinking…' }],
    }

    setChatError(null)
    setIsSubmittingMessage(true)
    setMessages((current) => [...current, optimisticUserMessage, pendingAssistantMessage])
    setDraft('')

    try {
      const targetSessionId = activeSessionId ?? (await createAndSelectSession())
      if (!targetSessionId) {
        throw new Error('Missing chat session')
      }

      const response = await submitChatMessage(targetSessionId, trimmedDraft, csrfToken)
      setMessages((current) =>
        current.flatMap((message) => {
          if (message.id === optimisticUserMessage.id) {
            return [response.user_message]
          }

          if (message.id === pendingAssistantMessage.id) {
            return [response.assistant_message]
          }

          return [message]
        }),
      )
      await refreshSessions(targetSessionId)
    } catch {
      setMessages((current) =>
        current.flatMap((message) => {
          if (message.id === pendingAssistantMessage.id) {
            return [
              {
                id: `error-assistant-${createdAt}`,
                role: 'assistant',
                created_at: new Date().toISOString(),
                content_blocks: [
                  {
                    type: 'text',
                    text: 'I couldn’t respond just now. Please try again.',
                  },
                ],
              },
            ]
          }

          return [message]
        }),
      )
      setChatError('We could not generate a reply right now.')
    } finally {
      setIsSubmittingMessage(false)
    }
  }

  return (
    <aside className="paper-panel chat-panel">
      <header className="chat-panel-header">
        <div>
          <p className="eyebrow">Assistant</p>
          <h2>Conversation</h2>
        </div>
        <p className="chat-panel-copy">
          Ask grounded, read-only questions about your synced schedule.
        </p>
      </header>

      <ChatSessionSwitcher
        activeSessionId={activeSessionId}
        isCreating={isCreatingSession}
        isLoading={isSessionsLoading}
        sessions={sessions}
        onCreateSession={handleCreateSession}
        onSelectSession={(sessionId) => {
          startTransition(() => setActiveSessionId(sessionId))
        }}
      />

      <ChatStatusLine text={chatError} tone="error" />

      <div className="chat-panel-body">
        <MessageList isLoading={isMessagesLoading} messages={messages} />
      </div>

      <ChatComposer
        disabled={isSubmittingMessage || isCreatingSession}
        value={draft}
        onChange={setDraft}
        onSubmit={handleSubmitMessage}
      />
    </aside>
  )
}

function CalendarWorkspace({
  session,
  onRefreshSession,
}: {
  session: AuthSession
  onRefreshSession: () => Promise<void>
}) {
  const [visibleWeekStart, setVisibleWeekStart] = useState(() => getStartOfWeek(new Date()))
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [syncStatus, setSyncStatus] = useState<CalendarSyncStatus | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [isCalendarLoading, setIsCalendarLoading] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [calendarError, setCalendarError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const loadCalendar = async () => {
      if (!session.user) {
        return
      }

      setIsCalendarLoading(true)
      setCalendarError(null)

      try {
        let nextSyncStatus = await fetchCalendarSyncStatus()

        if (nextSyncStatus.sync_state === 'not_started') {
          setIsSyncing(true)
          await triggerCalendarSync(getCookie('csrftoken'))
          nextSyncStatus = await fetchCalendarSyncStatus()
        }

        const range = toApiDateRange(visibleWeekStart)
        const eventsResponse = await fetchCalendarEvents(range)

        if (!cancelled) {
          setSyncStatus(nextSyncStatus)
          setEvents(eventsResponse.events)
        }
      } catch {
        if (!cancelled) {
          setCalendarError('We could not load your weekly calendar right now.')
        }
      } finally {
        if (!cancelled) {
          setIsSyncing(false)
          setIsCalendarLoading(false)
        }
      }
    }

    void loadCalendar()

    return () => {
      cancelled = true
    }
  }, [session.user, visibleWeekStart])

  if (!session.user) {
    return <Navigate to="/" replace />
  }

  const selectedEvent = events.find((event) => event.id === selectedEventId) ?? null
  const weekDays = buildWeekDays(visibleWeekStart)
  const csrfToken = getCookie('csrftoken')
  const activeTimeZone =
    events.find((event) => Boolean(event.timezone))?.timezone ||
    Intl.DateTimeFormat().resolvedOptions().timeZone ||
    'UTC'
  const initialCalendarScrollTop = getInitialCalendarScrollTop(events)

  const handleLogout = async () => {
    setActionError(null)

    try {
      await logoutUser()
      await onRefreshSession()
    } catch {
      setActionError('We could not sign you out cleanly. Please try again.')
    }
  }

  const handleRetrySync = async () => {
    setActionError(null)
    setIsSyncing(true)

    try {
      await triggerCalendarSync(csrfToken)
      const nextSyncStatus = await fetchCalendarSyncStatus()
      const range = toApiDateRange(visibleWeekStart)
      const eventsResponse = await fetchCalendarEvents(range)
      setSyncStatus(nextSyncStatus)
      setEvents(eventsResponse.events)
      setCalendarError(null)
    } catch {
      setActionError('We could not refresh the calendar sync. Please try again.')
    } finally {
      setIsSyncing(false)
    }
  }

  return (
    <main className="workspace-page">
      <header className="workspace-topbar">
        <div className="workspace-brand-row">
          <p className="workspace-wordmark">Cal Assistant</p>
          <nav aria-label="Primary navigation" className="workspace-primary-nav">
            <a className="is-active" href="/">
              Workspace
            </a>
            <span>Analytics</span>
            <span>Settings</span>
          </nav>
        </div>

        <div className="workspace-account-bar">
          <p className="workspace-account-mode">Workspace mode</p>
          <p className="workspace-account-email">{session.user.email}</p>
          <button className="secondary-button button-sm workspace-signout" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      <section className="workspace-layout">
        <aside className="paper-panel workspace-left-rail">
          <div className="workspace-left-header">
            <p className="eyebrow">Assistant</p>
            <p className="workspace-left-caption">Grounded weekly planning</p>
          </div>

          <nav className="workspace-left-nav" aria-label="Calendar sections">
            <button className="workspace-left-link" type="button">Today</button>
            <button className="workspace-left-link is-active" type="button">Workspace</button>
            <button className="workspace-left-link" type="button">Archives</button>
            <button className="workspace-left-link" type="button">Drafts</button>
          </nav>

          <button
            className="primary-button button-md workspace-left-cta"
            disabled={isSyncing}
            onClick={handleRetrySync}
          >
            {isSyncing ? 'Syncing…' : 'Sync Calendar'}
          </button>
        </aside>

        <section className="workspace-main-column">
          <header className="workspace-header editorial-header">
            <div className="workspace-title-group">
              <p className="eyebrow">Workspace</p>
              <h1>Your workspace</h1>
              <p className="workspace-intro">
                Review your synced week and ask grounded, read-only questions about
                what&apos;s ahead.
              </p>
            </div>
          </header>

          {actionError ? <p className="error-text">{actionError}</p> : null}

          <section className="calendar-workspace">
            <div className="calendar-main">
              <section className="paper-panel calendar-toolbar-panel">
                <div className="calendar-toolbar-row">
                  <div>
                    <p className="eyebrow">Weekly View</p>
                    <h2>{formatWeekRange(visibleWeekStart)}</h2>
                    <p className="calendar-timezone-label">Timezone: {activeTimeZone}</p>
                  </div>
                  <div className="calendar-toolbar-actions">
                    <button
                      className="secondary-button button-md"
                      onClick={() => setVisibleWeekStart((current) => getPreviousWeekStart(current))}
                    >
                      Previous Week
                    </button>
                    <button
                      className="secondary-button button-md"
                      onClick={() => setVisibleWeekStart((current) => getNextWeekStart(current))}
                    >
                      Next Week
                    </button>
                    <button
                      className="primary-button button-md"
                      disabled={isSyncing}
                      onClick={handleRetrySync}
                    >
                      {isSyncing ? 'Syncing…' : 'Sync Calendar'}
                    </button>
                  </div>
                </div>
                <SyncStatusIndicator syncStatus={syncStatus} isLoading={isCalendarLoading} />
              </section>

              <section className="paper-panel calendar-board">
                {calendarError ? (
                  <div className="calendar-empty-state">
                    <p className="eyebrow">Calendar Error</p>
                    <h2>We couldn&apos;t load this week</h2>
                    <p>{calendarError}</p>
                  </div>
                ) : null}

                {!calendarError && !isCalendarLoading && events.length === 0 ? (
                  <div className="calendar-empty-state">
                    <p className="eyebrow">Calendar Empty</p>
                    <h2>No events for this week</h2>
                    <p>Your synced planner is clear for the selected range.</p>
                  </div>
                ) : null}

                {!calendarError && (
                  <CalendarWeekView
                    events={events}
                    isLoading={isCalendarLoading}
                    scrollTargetTop={initialCalendarScrollTop}
                    selectedEventId={selectedEventId}
                    weekDays={weekDays}
                    onSelectEvent={(eventId) => setSelectedEventId(eventId)}
                  />
                )}
              </section>
            </div>

            <div className="calendar-side-column">
              <ChatWorkspace csrfToken={csrfToken} />

              <EventDetailsPanel
                event={selectedEvent}
                onboardingCompleted={session.user.onboarding_completed}
              />
            </div>
          </section>
        </section>
      </section>
    </main>
  )
}

function AppRoutes() {
  const location = useLocation()
  const [session, setSession] = useState<AuthSession | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

  const loadSession = async () => {
    setHasError(false)
    setIsLoading(true)

    try {
      await ensureCsrfCookie()
      const nextSession = await fetchSession()
      setSession(nextSession)
    } catch {
      setHasError(true)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadSession()
  }, [location.pathname])

  if (isLoading) {
    return <LoadingScreen />
  }

  if (hasError) {
    return (
      <ErrorScreen
        title="The backend session could not be loaded"
        message="Check that the Django backend is running and try again."
        onRetry={() => {
          void loadSession()
        }}
      />
    )
  }

  return (
    <Routes>
      <Route path="/auth/error" element={<AuthErrorPage />} />
      <Route
        path="/"
        element={
          session?.authenticated ? (
            <CalendarWorkspace session={session} onRefreshSession={loadSession} />
          ) : (
            <LoginPage />
          )
        }
      />
    </Routes>
  )
}

function App() {
  return <AppRoutes />
}

export default App
