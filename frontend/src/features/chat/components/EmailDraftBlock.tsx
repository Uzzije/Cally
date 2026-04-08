import type { EmailDraftBlock as EmailDraftBlockType } from '../types'
import { hasSuggestedTimesInEmailDraft } from '../utils/emailDraft'


function getDraftStatusLabel(block: EmailDraftBlockType) {
  if (block.status_detail) {
    return block.status_detail
  }

  return 'Draft only. Not sent.'
}

export function EmailDraftBlock({
  block,
  onBlockSuggestedTimes,
  onCopy,
}: {
  block: EmailDraftBlockType
  onBlockSuggestedTimes?: (block: EmailDraftBlockType) => void
  onCopy?: (block: EmailDraftBlockType) => void
}) {
  const canBlockSuggestedTimes = hasSuggestedTimesInEmailDraft(block)

  return (
    <article className="email-draft-block" aria-label="Email draft preview">
      <div className="email-draft-header">
        <div>
          <p className="email-draft-eyebrow">Email draft</p>
          <h3 className="email-draft-title">{block.subject}</h3>
        </div>
        <span className="email-draft-status">Draft</span>
      </div>
      <div className="email-draft-fields">
        <p className="email-draft-field">
          <span>To</span>
          <strong>{block.to.join(', ')}</strong>
        </p>
        {block.cc && block.cc.length > 0 ? (
          <p className="email-draft-field">
            <span>Cc</span>
            <strong>{block.cc.join(', ')}</strong>
          </p>
        ) : null}
      </div>
      <div className="email-draft-actions">
        <button className="secondary-button button-sm" onClick={() => onCopy?.(block)} type="button">
          Copy email
        </button>
        <button
          className="secondary-button button-sm"
          disabled={!canBlockSuggestedTimes}
          onClick={() => onBlockSuggestedTimes?.(block)}
          type="button"
        >
          Block suggested times
        </button>
      </div>
      {!canBlockSuggestedTimes ? (
        <p className="email-draft-action-note">
          This draft does not include suggested times to block yet.
        </p>
      ) : null}
      <pre className="email-draft-body">{block.body}</pre>
      <p className="email-draft-note">{getDraftStatusLabel(block)}</p>
    </article>
  )
}
