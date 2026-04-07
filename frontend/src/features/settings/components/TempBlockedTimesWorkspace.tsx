import { Navigate } from 'react-router-dom'
import { useState } from 'react'

import { WorkspacePageHeader } from '../../../app/layout/WorkspacePageHeader'
import { WorkspaceTopbar } from '../../../app/layout/WorkspaceTopbar'
import { logoutUser } from '../../auth/api/authClient'
import type { AuthSession } from '../../auth/types'
import type { MessageCreditStatus } from '../../chat/types'
import type { TempBlockedTimeEntry } from '../types'
import { TempBlockedTimesPage } from './TempBlockedTimesPage'


type TempBlockedTimesWorkspaceProps = {
  entries: TempBlockedTimeEntry[]
  messageCredits: MessageCreditStatus | null
  session: AuthSession
  onClearAll: () => Promise<void>
  onRefreshSession: () => Promise<void>
  onRemove: (entryId: string) => Promise<void>
}

export function TempBlockedTimesWorkspace({
  entries,
  messageCredits,
  session,
  onClearAll,
  onRefreshSession,
  onRemove,
}: TempBlockedTimesWorkspaceProps) {
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
          <WorkspacePageHeader
            eyebrow="Temp Blocked Times"
            intro="Reserve candidate meeting windows while you coordinate scheduling."
            title="Temporary holds"
          />

          {actionError ? <p className="error-text">{actionError}</p> : null}

          <TempBlockedTimesPage
            entries={entries}
            onClearAll={handleClearAll}
            onRemove={handleRemove}
          />
        </section>
      </section>
    </main>
  )
}
