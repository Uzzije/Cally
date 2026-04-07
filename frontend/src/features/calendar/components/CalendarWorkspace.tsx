import { Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { WorkspacePageHeader } from '../../../app/layout/WorkspacePageHeader'
import { WorkspaceTopbar } from '../../../app/layout/WorkspaceTopbar'
import { UpgradeNotice } from '../../../components/UpgradeNotice'
import { logoutUser } from '../../auth/api/authClient'
import type { AuthSession } from '../../auth/types'
import type { MessageCreditStatus } from '../../chat/types'
import type { BlockedTimeEntry, ExecutionMode, TempBlockedTimeEntry } from '../../settings/types'
import {
  fetchPreferences,
} from '../../settings/api/settingsClient'
import {
  fetchCalendarEvents,
  fetchCalendarSyncStatus,
  triggerCalendarSync,
} from '../api/calendarClient'
import type { CalendarEvent, CalendarSyncStatus } from '../types'
import { getInitialCalendarScrollTop } from '../utils/layout'
import {
  buildWeekDays,
  buildWeekOptions,
  formatWeekRange,
  getNextWeekStart,
  getPreviousWeekStart,
  getStartOfWeek,
  toApiDateRange,
} from '../utils/week'
import { EventDetailsPanel } from './EventDetailsPanel'
import { CalendarWeekView } from './CalendarWeekView'
import { SyncStatusIndicator } from './SyncStatusIndicator'
import { ChatWorkspace } from '../../chat/components/ChatWorkspace'
import type { EmailDraftBlock } from '../../chat/types'
import {
  buildEmailDraftClipboardText,
  extractTempBlockedTimesFromEmailDraft,
} from '../../chat/utils/emailDraft'
import { getCookie } from '../../../shared/lib/cookies'


const MULTI_CALENDAR_UPGRADE_LABEL =
  'Multi-calendar scope is part of an upgrade feature and is disabled for now.'

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

type CalendarWorkspaceProps = {
  messageCredits: MessageCreditStatus | null
  session: AuthSession
  tempBlockedTimes: TempBlockedTimeEntry[]
  onAddTempBlockedTimes: (entries: TempBlockedTimeEntry[]) => Promise<void>
  onRefreshMessageCredits: () => Promise<void>
  onRefreshSession: () => Promise<void>
}

export function CalendarWorkspace({
  messageCredits,
  session,
  tempBlockedTimes,
  onAddTempBlockedTimes,
  onRefreshMessageCredits,
  onRefreshSession,
}: CalendarWorkspaceProps) {
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
          <WorkspacePageHeader
            eyebrow="Workspace"
            intro="Review your synced week, inspect proposals, and explicitly approve the safe calendar changes you want to keep."
            title="Your workspace"
          />

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
                      <UpgradeNotice
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

                {!calendarError ? (
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
                ) : null}
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
