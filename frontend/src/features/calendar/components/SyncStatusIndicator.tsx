import type { CalendarSyncStatus } from '../types'


export function SyncStatusIndicator({
  syncStatus,
  isLoading,
  timeZone,
}: {
  syncStatus: CalendarSyncStatus | null
  isLoading: boolean
  timeZone: string
}) {
  if (isLoading) {
    return <p className="calendar-sync-meta">Last synced: Checking…</p>
  }

  if (!syncStatus) {
    return null
  }

  if (!syncStatus.last_synced_at) {
    return <p className="calendar-sync-meta">Last synced: Not yet synced</p>
  }

  const parsedDate = new Date(syncStatus.last_synced_at)
  if (Number.isNaN(parsedDate.getTime())) {
    return <p className="calendar-sync-meta">Last synced: Unavailable</p>
  }

  const formattedTimestamp = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone,
  }).format(parsedDate)

  return <p className="calendar-sync-meta">Last synced: {formattedTimestamp}</p>
}
