import type { ExecutionMode } from '../../settings/types'
import type { ChatMessage, EmailDraftBlock } from '../types'
import { MessageBlockRenderer } from './MessageBlockRenderer'


export function MessageList({
  messages,
  isLoading,
  activeProposalId = null,
  executionMode = null,
  isPreferencesLoading = false,
  onBlockSuggestedTimes,
  onCopyEmailDraft,
  onApproveAction,
  onRejectAction,
  onSaveChart,
  saveChartStates,
}: {
  messages: ChatMessage[]
  isLoading: boolean
  activeProposalId?: string | null
  executionMode?: ExecutionMode | null
  isPreferencesLoading?: boolean
  onBlockSuggestedTimes?: (block: EmailDraftBlock) => void
  onCopyEmailDraft?: (block: EmailDraftBlock) => void
  onApproveAction?: (proposalId: string) => void
  onRejectAction?: (proposalId: string) => void
  onSaveChart?: (messageId: number, blockIndex: number) => void
  saveChartStates?: Record<
    string,
    {
      status: 'idle' | 'saving' | 'saved' | 'error'
      error?: string | null
    }
  >
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
            {message.role === 'assistant' ? 'Cally' : 'You'}
          </p>
          <div className="chat-message-body">
            {message.pending && message.role === 'assistant' ? (
              <div className="chat-thinking" aria-label="Cally is thinking">
                <span className="chat-thinking-dot" />
                <span className="chat-thinking-dot" />
                <span className="chat-thinking-dot" />
              </div>
            ) : (
              message.content_blocks.map((block, index) => {
                const saveKey = `${message.id}:${index}`
                const saveState = saveChartStates?.[saveKey]

                return (
                <MessageBlockRenderer
                  activeProposalId={activeProposalId}
                  key={`${message.id}-${block.type}-${index}`}
                  block={block}
                  blockIndex={index}
                  executionMode={executionMode}
                  isPreferencesLoading={isPreferencesLoading}
                  messageId={message.id}
                  onBlockSuggestedTimes={onBlockSuggestedTimes}
                  onCopyEmailDraft={onCopyEmailDraft}
                  onApproveAction={onApproveAction}
                  onRejectAction={onRejectAction}
                  onSaveChart={onSaveChart}
                  saveChartError={saveState?.error}
                  saveChartState={saveState?.status ?? 'idle'}
                />
                )
              })
            )}
          </div>
        </article>
      ))}
    </div>
  )
}
