import { useEffect, useState } from 'react'

import {
  deleteAccount,
  fetchPreferences,
  SettingsClientError,
  updatePreferences,
} from '../api/settingsClient'
import type {
  BlockedTimeEntry,
  ExecutionMode,
  SettingsFieldErrors,
  UserPreferences,
} from '../types'
import { getDisplayTimezoneOptions } from '../timezones'
import { BlockedTimeList } from './BlockedTimeList'
import { ExecutionModeControl } from './ExecutionModeControl'


type SettingsPageProps = {
  csrfToken: string
  onAccountDeleted: () => Promise<void>
}

function createEmptyBlockedTime(): BlockedTimeEntry {
  const uniqueId =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`

  return {
    id: `blocked-time-${uniqueId}`,
    label: '',
    days: ['mon'],
    start: '09:00',
    end: '10:00',
  }
}

function getFieldError(fieldErrors: SettingsFieldErrors, fieldName: string) {
  return fieldErrors[fieldName]?.[0] ?? null
}

export function SettingsPage({ csrfToken, onAccountDeleted }: SettingsPageProps) {
  const [preferences, setPreferences] = useState<UserPreferences | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<SettingsFieldErrors>({})
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [isDeletingAccount, setIsDeletingAccount] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const displayTimezoneOptions = getDisplayTimezoneOptions(preferences?.display_timezone)

  useEffect(() => {
    let cancelled = false

    const loadPreferences = async () => {
      setIsLoading(true)
      setPageError(null)

      try {
        const nextPreferences = await fetchPreferences()
        if (!cancelled) {
          setPreferences(nextPreferences)
        }
      } catch {
        if (!cancelled) {
          setPageError('We could not load your planning preferences right now.')
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadPreferences()

    return () => {
      cancelled = true
    }
  }, [])

  const updateBlockedTime = (id: string, changes: Partial<BlockedTimeEntry>) => {
    setPreferences((current) => {
      if (!current) {
        return current
      }

      return {
        ...current,
        blocked_times: current.blocked_times.map((entry) =>
          entry.id === id ? { ...entry, ...changes } : entry,
        ),
      }
    })
  }

  const setExecutionMode = (executionMode: ExecutionMode) => {
    setPreferences((current) => (current ? { ...current, execution_mode: executionMode } : current))
  }

  const setDisplayTimezone = (displayTimezone: string) => {
    setPreferences((current) =>
      current ? { ...current, display_timezone: displayTimezone || null } : current,
    )
  }

  const addBlockedTime = () => {
    setSaveMessage(null)
    setFieldErrors({})
    setPreferences((current) =>
      current
        ? { ...current, blocked_times: [...current.blocked_times, createEmptyBlockedTime()] }
        : current,
    )
  }

  const removeBlockedTime = (id: string) => {
    setSaveMessage(null)
    setFieldErrors({})
    setPreferences((current) =>
      current
        ? {
            ...current,
            blocked_times: current.blocked_times.filter((entry) => entry.id !== id),
          }
        : current,
    )
  }

  const handleSave = async () => {
    if (!preferences) {
      return
    }

    setIsSaving(true)
    setSaveMessage(null)
    setPageError(null)
    setFieldErrors({})

    try {
      const savedPreferences = await updatePreferences(preferences, csrfToken)
      setPreferences(savedPreferences)
      setSaveMessage('Preferences saved. The assistant will use these constraints in future turns.')
    } catch (error) {
      if (error instanceof SettingsClientError) {
        setFieldErrors(error.fieldErrors)
        setPageError(error.message)
      } else {
        setPageError('We could not save your planning preferences right now.')
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteAccount = async () => {
    setDeleteError(null)

    if (deleteConfirmation.trim() !== 'DELETE') {
      setDeleteError('Type DELETE exactly to confirm account deletion.')
      return
    }

    setIsDeletingAccount(true)
    try {
      await deleteAccount(csrfToken)
      await onAccountDeleted()
    } catch {
      setDeleteError('We could not delete your account right now. Please try again.')
    } finally {
      setIsDeletingAccount(false)
    }
  }

  if (isLoading) {
    return (
      <section className="paper-panel settings-page">
        <p className="eyebrow">Settings</p>
        <h1>Loading preferences</h1>
        <p className="settings-page-copy">
          Pulling your planning constraints and execution policy from the server.
        </p>
      </section>
    )
  }

  if (!preferences) {
    return (
      <section className="paper-panel settings-page">
        <p className="eyebrow">Settings</p>
        <h1>Preferences unavailable</h1>
        <p className="settings-page-copy">{pageError}</p>
      </section>
    )
  }

  return (
    <section className="settings-page-grid">
      <section className="paper-panel settings-page">
        <header className="settings-page-header">
          <div>
            <p className="eyebrow">Settings</p>
            <h1>Assistant memory and planning policy</h1>
          </div>
          <p className="settings-page-copy">
            Manage recurring blocked times and the safest execution posture before the
            assistant starts proposing or acting.
          </p>
        </header>

        {pageError ? <p className="error-text">{pageError}</p> : null}
        {saveMessage ? <p className="settings-success">{saveMessage}</p> : null}

        <div className="settings-stack">
          <ExecutionModeControl
            disabled={isSaving}
            error={getFieldError(fieldErrors, 'execution_mode')}
            value={preferences.execution_mode}
            onChange={setExecutionMode}
          />

          <section className="settings-section">
            <div className="settings-section-heading">
              <h2>Display timezone</h2>
              <p className="settings-section-copy">
                Choose the timezone used for calendar rendering and assistant planning context.
              </p>
            </div>
            <label className="settings-field" htmlFor="display-timezone">
              <span>Calendar and chat timezone</span>
              <select
                id="display-timezone"
                className="settings-input"
                disabled={isSaving}
                value={preferences.display_timezone ?? ''}
                onChange={(event) => setDisplayTimezone(event.target.value)}
              >
                <option value="">Use synced calendar default</option>
                {displayTimezoneOptions
                  .filter((timeZone) => timeZone)
                  .map((timeZone) => (
                    <option key={timeZone} value={timeZone}>
                      {timeZone}
                    </option>
                  ))}
              </select>
            </label>
            {getFieldError(fieldErrors, 'display_timezone') ? (
              <p className="settings-field-error">
                {getFieldError(fieldErrors, 'display_timezone')}
              </p>
            ) : null}
          </section>

          <BlockedTimeList
            disabled={isSaving}
            entries={preferences.blocked_times}
            error={getFieldError(fieldErrors, 'blocked_times')}
            onAdd={addBlockedTime}
            onChange={updateBlockedTime}
            onRemove={removeBlockedTime}
          />
        </div>

        <div className="settings-page-actions">
          <button
            className="primary-button button-md"
            disabled={isSaving}
            type="button"
            onClick={handleSave}
          >
            {isSaving ? 'Saving…' : 'Save settings'}
          </button>
        </div>

        <section className="settings-section settings-danger-zone">
          <div className="settings-section-heading">
            <h2>Delete account</h2>
            <p className="settings-section-copy">
              Permanently delete your account and associated workspace data. This action cannot
              be undone.
            </p>
          </div>
          {deleteError ? <p className="error-text">{deleteError}</p> : null}
          <label className="settings-field" htmlFor="delete-account-confirmation">
            <span>Type DELETE to confirm</span>
            <input
              id="delete-account-confirmation"
              className="settings-input"
              disabled={isDeletingAccount}
              onChange={(event) => setDeleteConfirmation(event.target.value)}
              placeholder="DELETE"
              type="text"
              value={deleteConfirmation}
            />
          </label>
          <div className="settings-page-actions">
            <button
              className="danger-button button-md"
              disabled={isDeletingAccount}
              type="button"
              onClick={handleDeleteAccount}
            >
              {isDeletingAccount ? 'Deleting account…' : 'Delete account'}
            </button>
          </div>
        </section>
      </section>

    </section>
  )
}
