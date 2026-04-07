import type { ExecutionMode } from '../../settings/types'
import type { ActionCardAction, ActionCardBlock as ActionCardBlockType } from '../types'


function getStatusLabel(status: string) {
  if (status === 'pending') {
    return 'Pending review'
  }

  if (status === 'executing') {
    return 'Creating event'
  }

  if (status === 'executed') {
    return 'Added to calendar'
  }

  if (status === 'failed') {
    return 'Action failed'
  }

  return status.replace('_', ' ')
}

function getStatusNote(action: ActionCardAction, executionMode: ExecutionMode | null) {
  if (action.status_detail) {
    return action.status_detail
  }

  if (action.status === 'pending' && executionMode === 'draft_only') {
    return 'Draft-only mode keeps this proposal review-only. Switch to Confirm in Settings to execute it.'
  }

  if (action.status === 'rejected') {
    return 'No calendar changes were made.'
  }

  if (action.status === 'executed') {
    return 'The primary calendar has been refreshed from server truth.'
  }

  if (action.status === 'failed') {
    return 'No calendar changes were committed.'
  }

  return 'Suggested from your calendar availability. No calendar changes have been made.'
}

export function ActionCardBlock({
  block,
  executionMode,
  isPreferencesLoading,
  activeProposalId,
  onApproveAction,
  onRejectAction,
}: {
  block: ActionCardBlockType
  executionMode: ExecutionMode | null
  isPreferencesLoading: boolean
  activeProposalId: string | null
  onApproveAction?: (proposalId: string) => void
  onRejectAction?: (proposalId: string) => void
}) {
  return (
    <section className="action-card-block" aria-label="Scheduling proposals">
      {block.actions.map((action) => (
        <article key={action.id} className="action-card">
          <div className="action-card-header">
            <p className="action-card-eyebrow">
              Scheduling suggestion
              {action.details.rank ? (
                <span className="action-card-rank">Rank {action.details.rank}</span>
              ) : null}
            </p>
            <span className={`action-card-status action-card-status-${action.status}`}>
              {getStatusLabel(action.status)}
            </span>
          </div>
          <h3 className="action-card-summary">{action.summary}</h3>
          <div className="action-card-detail-grid">
            {action.details.date ? (
              <p className="action-card-detail">
                <span>Date</span>
                <strong>{action.details.date}</strong>
              </p>
            ) : null}
            {action.details.time ? (
              <p className="action-card-detail">
                <span>Time</span>
                <strong>{action.details.time}</strong>
              </p>
            ) : null}
            {action.details.attendees.length > 0 ? (
              <p className="action-card-detail">
                <span>Attendees</span>
                <strong>{action.details.attendees.join(', ')}</strong>
              </p>
            ) : null}
          </div>
          {action.status === 'pending' ? (
            <div className="action-card-actions">
              <button
                className="primary-button button-sm"
                disabled={
                  isPreferencesLoading ||
                  executionMode === 'draft_only' ||
                  activeProposalId === action.id
                }
                onClick={() => onApproveAction?.(action.id)}
              >
                {activeProposalId === action.id ? 'Working…' : 'Approve'}
              </button>
              <button
                className="secondary-button button-sm"
                disabled={activeProposalId === action.id}
                onClick={() => onRejectAction?.(action.id)}
              >
                Reject
              </button>
            </div>
          ) : null}
          {action.details.why ? <p className="action-card-rationale">{action.details.why}</p> : null}
          <p className="action-card-note">{getStatusNote(action, executionMode)}</p>
        </article>
      ))}
    </section>
  )
}
