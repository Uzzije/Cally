import { NavLink } from 'react-router-dom'

import type { MessageCreditStatus } from '../../features/chat/types'


type WorkspaceTopbarProps = {
  email: string
  messageCredits: MessageCreditStatus | null
  tempBlockedTimesCount: number
  onLogout: () => Promise<void>
}

export function WorkspaceTopbar({
  email,
  messageCredits,
  tempBlockedTimesCount,
  onLogout,
}: WorkspaceTopbarProps) {
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
          <NavLink className={({ isActive }) => (isActive ? 'is-active' : '')} to="/temp-blocked-times">
            Temp Blocked Times
            {tempBlockedTimesCount > 0 ? (
              <span className="workspace-nav-count">{tempBlockedTimesCount}</span>
            ) : null}
          </NavLink>
          <NavLink className={({ isActive }) => (isActive ? 'is-active' : '')} to="/settings">
            Settings
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
