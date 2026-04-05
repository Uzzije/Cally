import type { ChatMessage } from '../types'
import { MessageBlockRenderer } from './MessageBlockRenderer'


export function MessageList({
  messages,
  isLoading,
}: {
  messages: ChatMessage[]
  isLoading: boolean
}) {
  if (isLoading) {
    return <div className="chat-empty-state">Loading conversation…</div>
  }

  if (messages.length === 0) {
    return (
      <div className="chat-empty-state">
        Start the conversation with a calendar question like “What does tomorrow look like?”
      </div>
    )
  }

  return (
    <div className="chat-message-list">
      {messages.map((message) => (
        <article
          key={message.id}
          className={`chat-message chat-message-${message.role}${message.pending ? ' is-pending' : ''}`}
        >
          <p className="chat-message-role">
            {message.role === 'assistant' ? 'Assistant' : 'You'}
          </p>
          <div className="chat-message-body">
            {message.pending && message.role === 'assistant' ? (
              <div className="chat-thinking" aria-label="Assistant is thinking">
                <span className="chat-thinking-dot" />
                <span className="chat-thinking-dot" />
                <span className="chat-thinking-dot" />
              </div>
            ) : (
              message.content_blocks.map((block, index) => (
                <MessageBlockRenderer
                  key={`${message.id}-${block.type}-${index}`}
                  block={block}
                />
              ))
            )}
          </div>
        </article>
      ))}
    </div>
  )
}
