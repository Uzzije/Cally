import type { ChatSessionSummary } from '../types'


export function ChatSessionSwitcher({
  sessions,
  activeSessionId,
  isLoading,
  isCreating,
  onCreateSession,
  onSelectSession,
}: {
  sessions: ChatSessionSummary[]
  activeSessionId: number | null
  isLoading: boolean
  isCreating: boolean
  onCreateSession: () => void
  onSelectSession: (sessionId: number) => void
}) {
  return (
    <section className="chat-session-switcher">
      <div className="chat-session-switcher-row">
        <p className="eyebrow">Conversations</p>
        <button
          className="secondary-button button-sm"
          disabled={isCreating}
          onClick={onCreateSession}
        >
          {isCreating ? 'Creating…' : 'New Chat'}
        </button>
      </div>

      {isLoading ? <p className="chat-session-muted">Loading sessions…</p> : null}

      {!isLoading && sessions.length === 0 ? (
        <p className="chat-session-muted">No previous conversations yet.</p>
      ) : null}

      {!isLoading && sessions.length > 0 ? (
        <div className="chat-session-list">
          {sessions.map((session) => (
            <button
              key={session.id}
              className={`chat-session-item${session.id === activeSessionId ? ' is-active' : ''}`}
              onClick={() => onSelectSession(session.id)}
              type="button"
            >
              <strong>{session.title}</strong>
              <span>{new Date(session.updated_at).toLocaleDateString()}</span>
            </button>
          ))}
        </div>
      ) : null}
    </section>
  )
}

