import type { ExecutionMode } from '../../settings/types'
import type { ChatContentBlock } from '../types'
import { ActionCardBlock } from './ActionCardBlock'
import { ChartBlock } from './ChartBlock'
import { EmailDraftBlock } from './EmailDraftBlock'


export function MessageBlockRenderer({
  activeProposalId,
  block,
  blockIndex,
  executionMode,
  isPreferencesLoading,
  messageId,
  onBlockSuggestedTimes,
  onCopyEmailDraft,
  onApproveAction,
  onRejectAction,
  onSaveChart,
  saveChartError,
  saveChartState,
}: {
  activeProposalId: string | null
  block: ChatContentBlock
  blockIndex: number
  executionMode: ExecutionMode | null
  isPreferencesLoading: boolean
  messageId: number | string
  onBlockSuggestedTimes?: (block: Extract<ChatContentBlock, { type: 'email_draft' }>) => void
  onCopyEmailDraft?: (block: Extract<ChatContentBlock, { type: 'email_draft' }>) => void
  onApproveAction?: (proposalId: string) => void
  onRejectAction?: (proposalId: string) => void
  onSaveChart?: (messageId: number, blockIndex: number) => void
  saveChartError?: string | null
  saveChartState?: 'idle' | 'saving' | 'saved' | 'error'
}) {
  if (block.type === 'action_card') {
    return (
      <ActionCardBlock
        activeProposalId={activeProposalId}
        block={block}
        executionMode={executionMode}
        isPreferencesLoading={isPreferencesLoading}
        onApproveAction={onApproveAction}
        onRejectAction={onRejectAction}
      />
    )
  }

  if (block.type === 'email_draft') {
    return (
      <EmailDraftBlock
        block={block}
        onBlockSuggestedTimes={onBlockSuggestedTimes}
        onCopy={onCopyEmailDraft}
      />
    )
  }

  if (block.type === 'chart') {
    return (
      <ChartBlock
        block={block}
        onSave={
          typeof messageId === 'number' && onSaveChart
            ? () => onSaveChart(messageId, blockIndex)
            : undefined
        }
        saveError={saveChartError}
        saveState={saveChartState}
      />
    )
  }

  if (block.type === 'clarification') {
    return <p className="chat-block chat-block-clarification">{block.text}</p>
  }

  if (block.type === 'status') {
    return <p className="chat-block chat-block-status">{block.text}</p>
  }

  return <p className="chat-block">{block.text}</p>
}
