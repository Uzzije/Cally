import { useId, useRef } from 'react'

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
  const sessionRadioName = useId()
  const accordionRef = useRef<HTMLDetailsElement | null>(null)

  const handleSelectSession = (sessionId: number) => {
    onSelectSession(sessionId)
    if (accordionRef.current) {
      accordionRef.current.open = false
    }
  }

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

      <details className="chat-session-accordion" ref={accordionRef}>
        <summary className="chat-session-summary">
          <span>Conversation history</span>
          <span className="chat-session-count">{sessions.length}</span>
        </summary>

        <div className="chat-session-accordion-body">
          {isLoading ? <p className="chat-session-muted">Loading sessions…</p> : null}

          {!isLoading && sessions.length === 0 ? (
            <p className="chat-session-muted">No previous conversations yet.</p>
          ) : null}

          {!isLoading && sessions.length > 0 ? (
            <div className="chat-session-list" role="radiogroup" aria-label="Conversation history">
              {sessions.map((session) => (
                <label
                  key={session.id}
                  className={`chat-session-item${session.id === activeSessionId ? ' is-active' : ''}`}
                >
                  <input
                    checked={session.id === activeSessionId}
                    className="chat-session-radio"
                    name={sessionRadioName}
                    onChange={() => handleSelectSession(session.id)}
                    type="radio"
                    value={session.id}
                  />
                  <span className="chat-session-item-copy">
                    <strong>{session.title}</strong>
                    <span>{new Date(session.updated_at).toLocaleDateString()}</span>
                  </span>
                </label>
              ))}
            </div>
          ) : null}
        </div>
      </details>
    </section>
  )
}
