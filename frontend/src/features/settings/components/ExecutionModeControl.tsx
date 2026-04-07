import type { ExecutionMode } from '../types'


const EXECUTION_MODE_OPTIONS: Array<{
  value: ExecutionMode
  label: string
  description: string
}> = [
  {
    value: 'draft_only',
    label: 'Draft only',
    description: 'Keep all assistant actions review-only for now.',
  },
  {
    value: 'confirm',
    label: 'Confirm first',
    description: 'Require approval before any future execution step.',
  },
]

type ExecutionModeControlProps = {
  disabled?: boolean
  error?: string | null
  value: ExecutionMode
  onChange: (value: ExecutionMode) => void
}

export function ExecutionModeControl({
  disabled = false,
  error,
  value,
  onChange,
}: ExecutionModeControlProps) {
  return (
    <section className="settings-section">
      <div className="settings-section-heading">
        <p className="eyebrow">Execution Mode</p>
        <h2>How should the assistant behave later?</h2>
        <p className="settings-section-copy">
          Start from the safest posture and keep policy explicit before proposal and
          execution work lands.
        </p>
      </div>

      <div className="execution-mode-grid" role="radiogroup" aria-label="Execution mode">
        {EXECUTION_MODE_OPTIONS.map((option) => (
          <label
            className={`execution-mode-card${value === option.value ? ' is-selected' : ''}`}
            key={option.value}
          >
            <input
              checked={value === option.value}
              disabled={disabled}
              name="execution-mode"
              type="radio"
              value={option.value}
              onChange={() => onChange(option.value)}
            />
            <span className="execution-mode-card-title">{option.label}</span>
            <span className="execution-mode-card-copy">{option.description}</span>
          </label>
        ))}
      </div>

      {error ? <p className="settings-field-error">{error}</p> : null}
    </section>
  )
}
