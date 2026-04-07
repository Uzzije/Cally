type UpgradeNoticeProps = {
  title: string
  body: string
  eyebrow?: string
  statusLabel?: string
  compact?: boolean
  className?: string
  ctaLabel?: string
  onCta?: () => void
}

export function UpgradeNotice({
  title,
  body,
  eyebrow = 'Upgrade Preview',
  statusLabel = 'Disabled for now',
  compact = false,
  className = '',
  ctaLabel,
  onCta,
}: UpgradeNoticeProps) {
  return (
    <section
      aria-label={title}
      className={`upgrade-scope-notice${compact ? ' is-compact' : ''}${className ? ` ${className}` : ''}`}
    >
      <div className="upgrade-scope-copy">
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
        <p>{body}</p>
      </div>
      {ctaLabel && onCta ? (
        <button className="primary-button button-md" onClick={onCta} type="button">
          {ctaLabel}
        </button>
      ) : (
        <span className="upgrade-pill" aria-label="Disabled upgrade feature">
          {statusLabel}
        </span>
      )}
    </section>
  )
}

type ComingSoonDialogProps = {
  ariaLabel: string
  title: string
  body: string
  className?: string
  onClose: () => void
}

export function ComingSoonDialog({
  ariaLabel,
  title,
  body,
  className = '',
  onClose,
}: ComingSoonDialogProps) {
  return (
    <div className="event-modal-overlay" onClick={onClose} role="presentation">
      <div
        aria-label={ariaLabel}
        aria-modal="true"
        className={`event-modal-dialog analytics-upgrade-dialog${className ? ` ${className}` : ''}`}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <button
          aria-label="Close upgrade notice"
          className="secondary-button button-sm event-modal-close"
          onClick={onClose}
          type="button"
        >
          Close
        </button>
        <div className="analytics-upgrade-dialog-copy">
          <p className="eyebrow">Coming Soon</p>
          <h2>{title}</h2>
          <p>{body}</p>
        </div>
      </div>
    </div>
  )
}
