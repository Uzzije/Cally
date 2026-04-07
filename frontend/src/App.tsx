import { startTransition, useCallback, useEffect, useRef, useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'

import { createSavedInsight } from './features/analytics/api/analyticsClient'
import { AnalyticsDashboardPage } from './features/analytics/components/AnalyticsDashboardPage'
import { UpgradeNotice } from './components/UpgradeNotice'
import {
  clearTempBlockedTimes,
  createTempBlockedTimes,
  deleteTempBlockedTime,
  fetchPreferences,
  fetchTempBlockedTimes,
} from './features/settings/api/settingsClient'
import { SettingsPage } from './features/settings/components/SettingsPage'
import { TempBlockedTimesPage } from './features/settings/components/TempBlockedTimesPage'
import type { BlockedTimeEntry, ExecutionMode, TempBlockedTimeEntry } from './features/settings/types'
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
  buildWeekOptions,
  buildWeekDays,
  formatWeekRange,
  getNextWeekStart,
  getPreviousWeekStart,
  getStartOfWeek,
  toApiDateRange,
} from './features/calendar/utils/week'
import {
  approveActionProposal,
  createChatSession,
  fetchChatCredits,
  fetchChatMessages,
  fetchChatSessions,
  fetchChatTurnStatus,
  rejectActionProposal,
  submitChatMessage,
} from './features/chat/api/chatClient'
import { ChatComposer } from './features/chat/components/ChatComposer'
import { ChatSessionSwitcher } from './features/chat/components/ChatSessionSwitcher'
import { ChatStatusLine } from './features/chat/components/ChatStatusLine'
import { MessageList } from './features/chat/components/MessageList'
import { buildEmailDraftClipboardText, extractTempBlockedTimesFromEmailDraft } from './features/chat/utils/emailDraft'
import type {
  ActionCardAction,
  ChatMessage,
  ChatSessionSummary,
  EmailDraftBlock,
  MessageCreditStatus,
} from './features/chat/types'


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
const CHAT_TURN_POLL_INTERVAL_MS = 3000

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

function WorkspaceTopbar({
  email,
  messageCredits,
  tempBlockedTimesCount,
  onLogout,
}: {
  email: string
  messageCredits: MessageCreditStatus | null
  tempBlockedTimesCount: number
  onLogout: () => Promise<void>
}) {
  const aiMessagesTooltip = messageCredits
    ? messageCredits.remaining > 0
      ? `You have ${messageCredits.remaining} AI messages left today. When you hit the daily limit, new chat replies pause until your limit resets. Upgrade for more messages and a higher daily cap.`
      : 'You have reached today\'s AI message limit. New chat replies pause until your limit resets. Upgrade for more messages and a higher daily cap.'
    : null

  return (
    <header className="workspace-topbar">
      <div className="workspace-brand-row">
        <p className="workspace-wordmark">Cal Assistant</p>
        <nav aria-label="Primary navigation" className="workspace-primary-nav">
          <NavLink className={({ isActive }) => (isActive ? 'is-active' : '')} end to="/">
            Workspace
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'is-active' : '')} to="/analytics">
            Analytics
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'is-active' : '')} to="/settings">
            Settings
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'is-active' : '')} to="/temp-blocked-times">
            Temp Blocked Times
            {tempBlockedTimesCount > 0 ? <span className="workspace-nav-count">{tempBlockedTimesCount}</span> : null}
          </NavLink>
        </nav>
      </div>

      <div className="workspace-account-bar">
        <div className="workspace-account-summary">
          <p className="workspace-account-mode">Workspace mode</p>
          {messageCredits ? (
            <div
              aria-label="AI message usage"
              className="workspace-usage-badge"
              tabIndex={0}
            >
              <span className="workspace-usage-badge-dot" aria-hidden="true" />
              <span className="workspace-usage-badge-copy">
                <span className="workspace-usage-badge-label">AI Messages</span>
                <strong className="workspace-usage-badge-count">
                  {messageCredits.remaining} / {messageCredits.limit}
                </strong>
              </span>
              <span className="workspace-usage-tooltip" role="tooltip">
                {aiMessagesTooltip}
              </span>
            </div>
          ) : null}
        </div>
        <p className="workspace-account-email">{email}</p>
        <button className="secondary-button button-sm workspace-signout" onClick={() => void onLogout()}>
          Sign out
        </button>
      </div>
    </header>
  )
}

const MULTI_CALENDAR_UPGRADE_LABEL = 'Multi-calendar scope is part of an upgrade feature and is disabled for now.'

function UpgradeScopeNotice({
  title,
  body,
  compact = false,
}: {
  title: string
  body: string
  compact?: boolean
}) {
  return (
    <UpgradeNotice body={body} compact={compact} title={title} />
  )
}

function CalendarScopeUpgradeCard() {
  return (
    <section aria-label="Calendar scope upgrade" className="calendar-scope-upgrade-card">
      <div className="calendar-scope-upgrade-copy">
        <p className="eyebrow">Calendar Scope</p>
        <h3>Multi-calendar selection</h3>
        <p>{MULTI_CALENDAR_UPGRADE_LABEL}</p>
      </div>

      <fieldset className="calendar-scope-upgrade-list" disabled>
        <legend className="sr-only">Calendar scope selection</legend>
        <label className="calendar-scope-option is-checked">
          <input checked disabled name="calendar-scope-primary" type="checkbox" />
          <span className="calendar-scope-option-copy">
            <strong>Primary calendar</strong>
            <span>Current workspace and assistant scope</span>
          </span>
        </label>
        <label className="calendar-scope-option">
          <input disabled name="calendar-scope-team" type="checkbox" />
          <span className="calendar-scope-option-copy">
            <strong>Team calendar</strong>
            <span>Upgrade feature preview</span>
          </span>
        </label>
        <label className="calendar-scope-option">
          <input disabled name="calendar-scope-personal" type="checkbox" />
          <span className="calendar-scope-option-copy">
            <strong>Personal calendar</strong>
            <span>Upgrade feature preview</span>
          </span>
        </label>
      </fieldset>
    </section>
  )
}

function ChatWorkspace({
  activeTimeZone,
  csrfToken,
  executionMode,
  isOpen,
  isPreferencesLoading,
  onRefreshMessageCredits,
  scopeNotice,
  onBlockSuggestedTimes,
  onCopyEmailDraft,
  onProposalExecuted,
}: {
  activeTimeZone: string
  csrfToken: string
  executionMode: ExecutionMode | null
  isOpen: boolean
  isPreferencesLoading: boolean
  onRefreshMessageCredits: () => Promise<void>
  scopeNotice: string
  onBlockSuggestedTimes: (block: EmailDraftBlock) => void
  onCopyEmailDraft: (block: EmailDraftBlock) => Promise<void>
  onProposalExecuted: () => Promise<void>
}) {
  const chatViewportRef = useRef<HTMLDivElement | null>(null)
  const pollingTimeoutsRef = useRef<number[]>([])
  const activeSessionIdRef = useRef<number | null>(null)
  const messagesRef = useRef<ChatMessage[]>([])
  const mountedRef = useRef(true)
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([])
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [chatError, setChatError] = useState<string | null>(null)
  const [activeProposalId, setActiveProposalId] = useState<string | null>(null)
  const [saveChartStates, setSaveChartStates] = useState<
    Record<
      string,
      {
        status: 'idle' | 'saving' | 'saved' | 'error'
        error?: string | null
      }
    >
  >({})
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

  const clearPollingTimeouts = () => {
    pollingTimeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId))
    pollingTimeoutsRef.current = []
  }

  const buildFallbackAssistantMessage = (messageId: string, text: string): ChatMessage => ({
    id: messageId,
    role: 'assistant',
    created_at: new Date().toISOString(),
    content_blocks: [{ type: 'text', text }],
  })

  const replaceMessageById = (targetId: number | string, nextMessage: ChatMessage) => {
    setMessages((current) =>
      current.flatMap((message) => (message.id === targetId ? [nextMessage] : [message])),
    )
  }

  const patchProposalInMessages = (
    proposalId: string,
    updater: (currentAction: ActionCardAction) => ActionCardAction,
  ) => {
    setMessages((current) =>
      current.map((message) => ({
        ...message,
        content_blocks: message.content_blocks.map((block) => {
          if (block.type !== 'action_card') {
            return block
          }

          return {
            ...block,
            actions: block.actions.map((action) =>
              action.id === proposalId ? updater(action) : action,
            ),
          }
        }),
      })),
    )
  }

  const pollChatTurn = (options: {
    sessionId: number
    turnId: number
    pendingAssistantMessageId: string
    fallbackMessageId: string
  }) => {
    const poll = async () => {
      if (!mountedRef.current || activeSessionIdRef.current !== options.sessionId) {
        return
      }

      try {
        const response = await fetchChatTurnStatus(options.sessionId, options.turnId)
        if (!mountedRef.current || activeSessionIdRef.current !== options.sessionId) {
          return
        }

        if (response.turn.status === 'completed') {
          clearPollingTimeouts()
          replaceMessageById(
            options.pendingAssistantMessageId,
            response.assistant_message ??
              buildFallbackAssistantMessage(
                options.fallbackMessageId,
                'I couldn’t respond just now. Please try again.',
              ),
          )
          await refreshSessions(options.sessionId)
          return
        }

        if (response.turn.status === 'failed') {
          clearPollingTimeouts()
          replaceMessageById(
            options.pendingAssistantMessageId,
            response.assistant_message ??
              buildFallbackAssistantMessage(
                options.fallbackMessageId,
                'I couldn’t respond just now. Please try again.',
              ),
          )
          setChatError('We could not generate a reply right now.')
          await refreshSessions(options.sessionId)
          return
        }

        const timeoutId = window.setTimeout(() => {
          void poll()
        }, CHAT_TURN_POLL_INTERVAL_MS)
        pollingTimeoutsRef.current.push(timeoutId)
      } catch {
        clearPollingTimeouts()
        replaceMessageById(
          options.pendingAssistantMessageId,
          buildFallbackAssistantMessage(
            options.fallbackMessageId,
            'I couldn’t respond just now. Please try again.',
          ),
        )
        setChatError('We could not generate a reply right now.')
      }
    }

    void poll()
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
    mountedRef.current = true
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
      mountedRef.current = false
      clearPollingTimeouts()
    }
  }, [csrfToken])

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId
    clearPollingTimeouts()
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

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  useEffect(() => {
    if (isMessagesLoading) {
      return
    }

    const viewport = chatViewportRef.current
    if (!viewport) {
      return
    }

    const scrollToLatestMessage = () => {
      if (typeof viewport.scrollTo === 'function') {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: 'auto',
        })
      }

      viewport.scrollTop = viewport.scrollHeight
    }

    const animationFrameId = window.requestAnimationFrame(scrollToLatestMessage)

    return () => {
      window.cancelAnimationFrame(animationFrameId)
    }
  }, [activeSessionId, isMessagesLoading, isOpen, messages])

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
      await onRefreshMessageCredits()
      replaceMessageById(optimisticUserMessage.id, response.user_message)
      pollChatTurn({
        sessionId: targetSessionId,
        turnId: response.turn.id,
        pendingAssistantMessageId: String(pendingAssistantMessage.id),
        fallbackMessageId: `error-assistant-${createdAt}`,
      })
    } catch {
      try {
        await onRefreshMessageCredits()
      } catch {
        // Keep the chat fallback path intact if the credit refresh fails too.
      }
      replaceMessageById(
        pendingAssistantMessage.id,
        buildFallbackAssistantMessage(
          `error-assistant-${createdAt}`,
          'I couldn’t respond just now. Please try again.',
        ),
      )
      setChatError('We could not generate a reply right now.')
    } finally {
      setIsSubmittingMessage(false)
    }
  }

  const findProposal = (proposalId: string) => {
    for (const message of messagesRef.current) {
      for (const block of message.content_blocks) {
        if (block.type !== 'action_card') {
          continue
        }

        const action = block.actions.find((candidate) => candidate.id === proposalId)
        if (action) {
          return action
        }
      }
    }

    return null
  }

  const handleApproveProposal = async (proposalId: string) => {
    if (!activeSessionId || activeProposalId) {
      return
    }

    const previousAction = findProposal(proposalId)
    if (!previousAction) {
      return
    }

    setChatError(null)
    setActiveProposalId(proposalId)
    patchProposalInMessages(proposalId, (current) => ({
      ...current,
      status: 'executing',
      status_detail: 'Creating the event on your primary calendar.',
    }))

    try {
      const proposal = await approveActionProposal(activeSessionId, proposalId, csrfToken)
      patchProposalInMessages(proposalId, () => proposal)
      if (proposal.status === 'executed') {
        await onProposalExecuted()
      }
    } catch (error) {
      patchProposalInMessages(proposalId, () => previousAction)
      setChatError(
        error instanceof Error ? error.message : 'We could not execute that proposal right now.',
      )
    } finally {
      setActiveProposalId(null)
    }
  }

  const handleRejectProposal = async (proposalId: string) => {
    if (!activeSessionId || activeProposalId) {
      return
    }

    setChatError(null)
    setActiveProposalId(proposalId)

    try {
      const proposal = await rejectActionProposal(activeSessionId, proposalId, csrfToken)
      patchProposalInMessages(proposalId, () => proposal)
    } catch (error) {
      setChatError(
        error instanceof Error ? error.message : 'We could not reject that proposal right now.',
      )
    } finally {
      setActiveProposalId(null)
    }
  }

  const handleSaveChart = async (messageId: number, blockIndex: number) => {
    const stateKey = `${messageId}:${blockIndex}`
    setSaveChartStates((current) => ({
      ...current,
      [stateKey]: {
        status: 'saving',
        error: null,
      },
    }))

    try {
      const savedInsight = await createSavedInsight(messageId, blockIndex, csrfToken)
      setSaveChartStates((current) => ({
        ...current,
        [stateKey]: {
          status: 'saved',
          error: savedInsight.replaced_existing
            ? 'Replaced your current saved insight. Upgrade to keep more.'
            : null,
        },
      }))
    } catch (error) {
      setSaveChartStates((current) => ({
        ...current,
        [stateKey]: {
          status: 'error',
          error: error instanceof Error ? error.message : 'Unable to save this insight right now.',
        },
      }))
    }
  }

  return (
    <aside className="paper-panel chat-panel">
      <header className="chat-panel-header">
        <div className="chat-panel-brand">
          <div className="chat-panel-mark" aria-hidden="true">
            <span className="brand-book chat-brand-book">
              <span />
              <span />
            </span>
          </div>
          <div>
            <p className="eyebrow">Assistant</p>
            <h2>Ask Cally</h2>
          </div>
        </div>
        <p className="chat-panel-copy">
          Ask grounded calendar questions and review suggested actions before anything changes.
        </p>
        <p className="chat-panel-timezone">Chat timezone: {activeTimeZone}</p>
      </header>

      <UpgradeScopeNotice
        compact
        body={scopeNotice}
        title="Assistant scope"
      />

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

      <div className="chat-panel-body" ref={chatViewportRef}>
        <MessageList
          activeProposalId={activeProposalId}
          executionMode={executionMode}
          isLoading={isMessagesLoading}
          isPreferencesLoading={isPreferencesLoading}
          messages={messages}
          onBlockSuggestedTimes={onBlockSuggestedTimes}
          onCopyEmailDraft={onCopyEmailDraft}
          onApproveAction={handleApproveProposal}
          onRejectAction={handleRejectProposal}
          onSaveChart={handleSaveChart}
          saveChartStates={saveChartStates}
        />
      </div>

      <ChatComposer
        disabled={isSubmittingMessage}
        value={draft}
        onChange={setDraft}
        onSubmit={handleSubmitMessage}
      />
    </aside>
  )
}

function CalendarWorkspace({
  messageCredits,
  session,
  tempBlockedTimes,
  onAddTempBlockedTimes,
  onRefreshMessageCredits,
  onRefreshSession,
}: {
  messageCredits: MessageCreditStatus | null
  session: AuthSession
  tempBlockedTimes: TempBlockedTimeEntry[]
  onAddTempBlockedTimes: (entries: TempBlockedTimeEntry[]) => Promise<void>
  onRefreshMessageCredits: () => Promise<void>
  onRefreshSession: () => Promise<void>
}) {
  const [visibleWeekStart, setVisibleWeekStart] = useState(() => getStartOfWeek(new Date()))
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [blockedTimes, setBlockedTimes] = useState<BlockedTimeEntry[]>([])
  const [executionMode, setExecutionMode] = useState<ExecutionMode | null>(null)
  const [syncStatus, setSyncStatus] = useState<CalendarSyncStatus | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [isCalendarLoading, setIsCalendarLoading] = useState(true)
  const [isPreferencesLoading, setIsPreferencesLoading] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [calendarError, setCalendarError] = useState<string | null>(null)
  const [preferencesError, setPreferencesError] = useState<string | null>(null)
  const [displayTimezone, setDisplayTimezone] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [isChatExpanded, setIsChatExpanded] = useState(false)
  const [isCalendarScopeVisible, setIsCalendarScopeVisible] = useState(false)

  const refreshCalendarWorkspace = async () => {
    const nextSyncStatus = await fetchCalendarSyncStatus()
    const range = toApiDateRange(visibleWeekStart)
    const eventsResponse = await fetchCalendarEvents(range)
    setSyncStatus(nextSyncStatus)
    setEvents(eventsResponse.events)
    setCalendarError(null)
  }

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

        if (!cancelled) {
          const range = toApiDateRange(visibleWeekStart)
          const eventsResponse = await fetchCalendarEvents(range)
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

  useEffect(() => {
    let cancelled = false

    const loadPreferences = async () => {
      if (!session.user) {
        return
      }

      setIsPreferencesLoading(true)
      setPreferencesError(null)

      try {
        const response = await fetchPreferences()
        if (!cancelled) {
          setBlockedTimes(response.blocked_times)
          setExecutionMode(response.execution_mode)
          setDisplayTimezone(response.display_timezone)
        }
      } catch {
        if (!cancelled) {
          setPreferencesError('Blocked-time overlays are unavailable right now.')
        }
      } finally {
        if (!cancelled) {
          setIsPreferencesLoading(false)
        }
      }
    }

    void loadPreferences()

    return () => {
      cancelled = true
    }
  }, [session.user])

  useEffect(() => {
    if (!selectedEventId) {
      return
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSelectedEventId(null)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [selectedEventId])

  if (!session.user) {
    return <Navigate to="/" replace />
  }

  const selectedEvent = events.find((event) => event.id === selectedEventId) ?? null
  const weekDays = buildWeekDays(visibleWeekStart)
  const weekOptions = buildWeekOptions(visibleWeekStart)
  const csrfToken = getCookie('csrftoken')
  const activeTimeZone =
    displayTimezone ||
    events.find((event) => Boolean(event.timezone))?.timezone ||
    Intl.DateTimeFormat().resolvedOptions().timeZone ||
    'UTC'
  const initialCalendarScrollTop = getInitialCalendarScrollTop(events, activeTimeZone)

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
      await refreshCalendarWorkspace()
    } catch {
      setActionError('We could not refresh the calendar sync. Please try again.')
    } finally {
      setIsSyncing(false)
    }
  }

  const handleCopyEmailDraft = async (block: EmailDraftBlock) => {
    setActionError(null)

    try {
      await navigator.clipboard.writeText(buildEmailDraftClipboardText(block))
    } catch {
      setActionError('We could not copy that email draft right now.')
    }
  }

  const handleBlockSuggestedTimes = async (block: EmailDraftBlock) => {
    const nextEntries = extractTempBlockedTimesFromEmailDraft(block)
    if (nextEntries.length === 0) {
      setActionError('We could not find any suggested times to block in that draft.')
      return
    }

    try {
      setActionError(null)
      await onAddTempBlockedTimes(nextEntries)
    } catch {
      setActionError('We could not save those temporary blocked times right now.')
    }
  }

  return (
    <main className="workspace-page">
      {isChatExpanded ? (
        <button
          aria-label="Close AI chat"
          className="chat-overlay-backdrop"
          onClick={() => setIsChatExpanded(false)}
          type="button"
        />
      ) : null}

      <WorkspaceTopbar
        email={session.user.email}
        messageCredits={messageCredits}
        tempBlockedTimesCount={tempBlockedTimes.length}
        onLogout={handleLogout}
      />

      <section className="workspace-layout workspace-layout-content-only">
        <section className="workspace-main-column">
          <header className="workspace-header editorial-header">
            <div className="workspace-title-group">
              <p className="eyebrow">Workspace</p>
              <h1>Your workspace</h1>
              <p className="workspace-intro">
                Review your synced week, inspect proposals, and explicitly approve
                the safe calendar changes you want to keep.
              </p>
            </div>
          </header>

          {actionError ? <p className="error-text">{actionError}</p> : null}

          <section className={`calendar-workspace${isChatExpanded ? ' is-chat-expanded' : ''}`}>
            <div className="calendar-main">
              <section className="paper-panel calendar-toolbar-panel">
                <div className="calendar-toolbar-row">
                  <div className="calendar-toolbar-copy">
                    <p className="eyebrow">Weekly View</p>
                    <h2>{formatWeekRange(visibleWeekStart)}</h2>
                    <p className="calendar-timezone-label">Timezone: {activeTimeZone}</p>
                  </div>
                  <div className="calendar-toolbar-actions">
                    <label className="calendar-week-picker" htmlFor="calendar-week-select">
                      <span>Jump to week</span>
                      <select
                        id="calendar-week-select"
                        aria-label="Jump to week"
                        className="calendar-week-select"
                        value={visibleWeekStart.toISOString()}
                        onChange={(event) => setVisibleWeekStart(new Date(event.target.value))}
                      >
                        {weekOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
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
                <div className="calendar-toolbar-status">
                  <SyncStatusIndicator syncStatus={syncStatus} isLoading={isCalendarLoading} />
                </div>
                {preferencesError ? (
                  <p className="calendar-preferences-note">{preferencesError}</p>
                ) : null}
                <section className="calendar-scope-section">
                  <div className="calendar-scope-section-header">
                    <div className="calendar-scope-section-copy">
                      <p className="eyebrow">Calendar Scope</p>
                    </div>
                    <button
                      aria-controls="calendar-scope-content"
                      aria-expanded={isCalendarScopeVisible}
                      className="secondary-button button-sm"
                      onClick={() => setIsCalendarScopeVisible((current) => !current)}
                      type="button"
                    >
                      {isCalendarScopeVisible ? 'Hide section' : 'Show section'}
                    </button>
                  </div>

                  {isCalendarScopeVisible ? (
                    <div className="calendar-scope-section-content" id="calendar-scope-content">
                      <CalendarScopeUpgradeCard />
                      <UpgradeScopeNotice
                        body="Workspace and assistant currently stay scoped to your synced primary calendar until the upgrade is enabled."
                        title="Current active scope"
                      />
                    </div>
                  ) : null}
                </section>
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
                    blockedTimes={isPreferencesLoading ? [] : blockedTimes}
                    events={events}
                    isLoading={isCalendarLoading}
                    scrollTargetTop={initialCalendarScrollTop}
                    selectedEventId={selectedEventId}
                    tempBlockedTimes={tempBlockedTimes}
                    timeZone={activeTimeZone}
                    weekDays={weekDays}
                    onSelectEvent={(eventId) => setSelectedEventId(eventId)}
                  />
                )}
              </section>
            </div>

            <div className={`calendar-chat-dock${isChatExpanded ? ' is-open' : ''}`}>
              <ChatWorkspace
                activeTimeZone={activeTimeZone}
                csrfToken={csrfToken}
                executionMode={executionMode}
                isOpen={isChatExpanded}
                isPreferencesLoading={isPreferencesLoading}
                onRefreshMessageCredits={onRefreshMessageCredits}
                scopeNotice="Assistant replies and suggested actions currently use your synced primary calendar only."
                onBlockSuggestedTimes={handleBlockSuggestedTimes}
                onCopyEmailDraft={handleCopyEmailDraft}
                onProposalExecuted={refreshCalendarWorkspace}
              />
            </div>
          </section>

          <button
            aria-expanded={isChatExpanded}
            aria-label={isChatExpanded ? 'Close Ask Cally' : 'Open Ask Cally'}
            className={`primary-button button-md chat-launcher${isChatExpanded ? ' is-open' : ''}`}
            onClick={() => setIsChatExpanded((current) => !current)}
            type="button"
          >
            <span className="chat-launcher-icon" aria-hidden="true">
              <span className="brand-book chat-launcher-book">
                <span />
                <span />
              </span>
            </span>
            <span>{isChatExpanded ? 'Close Ask Cally' : 'Ask Cally'}</span>
          </button>
        </section>
      </section>

      {selectedEvent ? (
        <div
          className="event-modal-overlay"
          onClick={() => setSelectedEventId(null)}
          role="presentation"
        >
          <div
            aria-label="Event details"
            aria-modal="true"
            className="event-modal-dialog"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <button
              aria-label="Close event details"
              className="secondary-button button-sm event-modal-close"
              onClick={() => setSelectedEventId(null)}
              type="button"
            >
              Close
            </button>
            <EventDetailsPanel
              event={selectedEvent}
              onboardingCompleted={session.user.onboarding_completed}
              timeZone={activeTimeZone}
            />
          </div>
        </div>
      ) : null}
    </main>
  )
}

function SettingsWorkspace({
  messageCredits,
  session,
  tempBlockedTimesCount,
  onRefreshSession,
}: {
  messageCredits: MessageCreditStatus | null
  session: AuthSession
  tempBlockedTimesCount: number
  onRefreshSession: () => Promise<void>
}) {
  const [actionError, setActionError] = useState<string | null>(null)

  if (!session.user) {
    return <Navigate to="/" replace />
  }

  const csrfToken = getCookie('csrftoken')

  const handleLogout = async () => {
    setActionError(null)

    try {
      await logoutUser()
      await onRefreshSession()
    } catch {
      setActionError('We could not sign you out cleanly. Please try again.')
    }
  }

  return (
    <main className="workspace-page">
      <WorkspaceTopbar
        email={session.user.email}
        messageCredits={messageCredits}
        tempBlockedTimesCount={tempBlockedTimesCount}
        onLogout={handleLogout}
      />

      <section className="workspace-layout settings-layout">
        <section className="workspace-main-column">
          <header className="workspace-header editorial-header">
            <div className="workspace-title-group">
              <p className="eyebrow">Settings</p>
              <h1>Preference-aware planning</h1>
              <p className="workspace-intro">
                Define the recurring constraints and execution posture the assistant
                should remember before it starts proposing or acting.
              </p>
            </div>
          </header>

          {actionError ? <p className="error-text">{actionError}</p> : null}

          <SettingsPage csrfToken={csrfToken} onAccountDeleted={onRefreshSession} />
        </section>
      </section>
    </main>
  )
}

function AnalyticsWorkspace({
  messageCredits,
  session,
  tempBlockedTimesCount,
  onRefreshSession,
}: {
  messageCredits: MessageCreditStatus | null
  session: AuthSession
  tempBlockedTimesCount: number
  onRefreshSession: () => Promise<void>
}) {
  const [actionError, setActionError] = useState<string | null>(null)

  if (!session.user) {
    return <Navigate to="/" replace />
  }

  const csrfToken = getCookie('csrftoken')

  const handleLogout = async () => {
    setActionError(null)

    try {
      await logoutUser()
      await onRefreshSession()
    } catch {
      setActionError('We could not sign you out cleanly. Please try again.')
    }
  }

  return (
    <main className="workspace-page">
      <WorkspaceTopbar
        email={session.user.email}
        messageCredits={messageCredits}
        tempBlockedTimesCount={tempBlockedTimesCount}
        onLogout={handleLogout}
      />

      <section className="workspace-layout settings-layout">
        <section className="workspace-main-column">
          <header className="workspace-header editorial-header">
            <div className="workspace-title-group">
              <p className="eyebrow">Analytics</p>
              <h1>Saved insights dashboard</h1>
              <p className="workspace-intro">
                Revisit the analytics charts worth keeping, then refresh or delete them
                without reopening the original chat thread.
              </p>
            </div>
          </header>

          {actionError ? <p className="error-text">{actionError}</p> : null}

          <AnalyticsDashboardPage csrfToken={csrfToken} />
        </section>
      </section>
    </main>
  )
}

function TempBlockedTimesWorkspace({
  entries,
  messageCredits,
  session,
  onClearAll,
  onRefreshSession,
  onRemove,
}: {
  entries: TempBlockedTimeEntry[]
  messageCredits: MessageCreditStatus | null
  session: AuthSession
  onClearAll: () => Promise<void>
  onRefreshSession: () => Promise<void>
  onRemove: (entryId: string) => Promise<void>
}) {
  const [actionError, setActionError] = useState<string | null>(null)

  if (!session.user) {
    return <Navigate to="/" replace />
  }

  const handleLogout = async () => {
    setActionError(null)

    try {
      await logoutUser()
      await onRefreshSession()
    } catch {
      setActionError('We could not sign you out cleanly. Please try again.')
    }
  }

  const handleClearAll = async () => {
    setActionError(null)

    try {
      await onClearAll()
    } catch {
      setActionError('We could not clear those temporary blocked times right now.')
    }
  }

  const handleRemove = async (entryId: string) => {
    setActionError(null)

    try {
      await onRemove(entryId)
    } catch {
      setActionError('We could not remove that temporary blocked time right now.')
    }
  }

  return (
    <main className="workspace-page">
      <WorkspaceTopbar
        email={session.user.email}
        messageCredits={messageCredits}
        tempBlockedTimesCount={entries.length}
        onLogout={handleLogout}
      />

      <section className="workspace-layout settings-layout">
        <section className="workspace-main-column">
          <header className="workspace-header editorial-header">
            <div className="workspace-title-group">
              <p className="eyebrow">Temp Blocked Times</p>
              <h1>Temporary holds</h1>
              <p className="workspace-intro">
                Reserve candidate meeting windows while you coordinate scheduling.
              </p>
            </div>
          </header>

          {actionError ? <p className="error-text">{actionError}</p> : null}

          <TempBlockedTimesPage entries={entries} onClearAll={handleClearAll} onRemove={handleRemove} />
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
  const [messageCredits, setMessageCredits] = useState<MessageCreditStatus | null>(null)
  const [tempBlockedTimes, setTempBlockedTimes] = useState<TempBlockedTimeEntry[]>([])

  const refreshTempBlockedTimes = async () => {
    const response = await fetchTempBlockedTimes()
    setTempBlockedTimes(response.entries)
  }

  const addTempBlockedTimes = async (entries: TempBlockedTimeEntry[]) => {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
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
    setTempBlockedTimes((current) => [...response.entries, ...current])
  }

  const removeTempBlockedTime = async (entryId: string) => {
    const response = await deleteTempBlockedTime(entryId, getCookie('csrftoken'))
    setTempBlockedTimes(response.entries)
  }

  const clearAllTempBlockedTimes = async () => {
    const response = await clearTempBlockedTimes(getCookie('csrftoken'))
    setTempBlockedTimes(response.entries)
  }

  const refreshMessageCredits = async () => {
    const response = await fetchChatCredits()
    setMessageCredits(response)
  }

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
      } else {
        setTempBlockedTimes([])
        setMessageCredits(null)
      }
    } catch {
      setHasError(true)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadSession()
  }, [location.pathname, loadSession])

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
            <CalendarWorkspace
              messageCredits={messageCredits}
              onAddTempBlockedTimes={addTempBlockedTimes}
              onRefreshMessageCredits={refreshMessageCredits}
              onRefreshSession={loadSession}
              session={session}
              tempBlockedTimes={tempBlockedTimes}
            />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        path="/analytics"
        element={
          session?.authenticated ? (
            <AnalyticsWorkspace
              messageCredits={messageCredits}
              onRefreshSession={loadSession}
              session={session}
              tempBlockedTimesCount={tempBlockedTimes.length}
            />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        path="/settings"
        element={
          session?.authenticated ? (
            <SettingsWorkspace
              messageCredits={messageCredits}
              onRefreshSession={loadSession}
              session={session}
              tempBlockedTimesCount={tempBlockedTimes.length}
            />
          ) : (
            <LoginPage />
          )
        }
      />
      <Route
        path="/temp-blocked-times"
        element={
          session?.authenticated ? (
            <TempBlockedTimesWorkspace
              entries={tempBlockedTimes}
              messageCredits={messageCredits}
              onClearAll={clearAllTempBlockedTimes}
              onRefreshSession={loadSession}
              onRemove={removeTempBlockedTime}
              session={session}
            />
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
