import type { CalendarSyncStatus } from '../types'


export function SyncStatusIndicator({
  syncStatus,
  isLoading,
}: {
  syncStatus: CalendarSyncStatus | null
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <div className="status-ribbon">
        <span className="status-dot" aria-hidden="true" />
        <span>Loading calendar state…</span>
      </div>
    )
  }

  if (!syncStatus) {
    return null
  }

  const copyByState: Record<string, string> = {
    not_started: 'Calendar not synced yet',
    syncing: 'Syncing your primary calendar',
    ready: 'Synced and ready',
    stale: 'Data is visible, but freshness may be lagging',
  }

  return (
    <div className="status-ribbon">
      <span className="status-dot" aria-hidden="true" />
      <span>{copyByState[syncStatus.sync_state] ?? 'Calendar status available'}</span>
    </div>
  )
}
