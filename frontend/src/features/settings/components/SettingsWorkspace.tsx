import { Navigate } from 'react-router-dom'
import { useState } from 'react'

import { WorkspacePageHeader } from '../../../app/layout/WorkspacePageHeader'
import { WorkspaceTopbar } from '../../../app/layout/WorkspaceTopbar'
import { logoutUser } from '../../auth/api/authClient'
import type { AuthSession } from '../../auth/types'
import type { MessageCreditStatus } from '../../chat/types'
import { getCookie } from '../../../shared/lib/cookies'
import { SettingsPage } from './SettingsPage'


type SettingsWorkspaceProps = {
  messageCredits: MessageCreditStatus | null
  session: AuthSession
  tempBlockedTimesCount: number
  onRefreshSession: () => Promise<void>
}

export function SettingsWorkspace({
  messageCredits,
  session,
  tempBlockedTimesCount,
  onRefreshSession,
}: SettingsWorkspaceProps) {
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
          <WorkspacePageHeader
            eyebrow="Settings"
            intro="Set your preferences so Cally knows how you like to work."
            title="Preference-aware planning"
          />

          {actionError ? <p className="error-text">{actionError}</p> : null}

          <SettingsPage csrfToken={csrfToken} onAccountDeleted={onRefreshSession} />
        </section>
      </section>
    </main>
  )
}
