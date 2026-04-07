import type { BlockedTimeEntry, WeekdayCode } from '../types'


const WEEKDAY_OPTIONS: Array<{ code: WeekdayCode; label: string }> = [
  { code: 'mon', label: 'Mon' },
  { code: 'tue', label: 'Tue' },
  { code: 'wed', label: 'Wed' },
  { code: 'thu', label: 'Thu' },
  { code: 'fri', label: 'Fri' },
  { code: 'sat', label: 'Sat' },
  { code: 'sun', label: 'Sun' },
]

type BlockedTimeListProps = {
  disabled?: boolean
  entries: BlockedTimeEntry[]
  error?: string | null
  onAdd: () => void
  onChange: (id: string, changes: Partial<BlockedTimeEntry>) => void
  onRemove: (id: string) => void
}

export function BlockedTimeList({
  disabled = false,
  entries,
  error,
  onAdd,
  onChange,
  onRemove,
}: BlockedTimeListProps) {
  return (
    <section className="settings-section">
      <div className="settings-section-heading">
        <p className="eyebrow">Blocked Time</p>
        <h2>Protect recurring constraints</h2>
        <p className="settings-section-copy">
          Add weekly planning blocks the assistant should remember and the workspace
          should show as protected time.
        </p>
      </div>

      <div className="settings-list-header">
        <p className="settings-list-copy">Recurring weekly blocks</p>
        <button
          className="secondary-button button-sm"
          disabled={disabled}
          type="button"
          onClick={onAdd}
        >
          Add blocked time
        </button>
      </div>

      {entries.length === 0 ? (
        <div className="settings-empty-state">
          <p>No blocked times configured yet.</p>
          <p>Add recurring focus, workout, commute, or family windows here.</p>
        </div>
      ) : null}

      <div className="blocked-time-list">
        {entries.map((entry, index) => (
          <article className="blocked-time-card" key={entry.id}>
            <div className="blocked-time-card-header">
              <div>
                <p className="blocked-time-index">Block {index + 1}</p>
                <p className="blocked-time-summary">{entry.label || 'Untitled block'}</p>
              </div>
              <button
                className="secondary-button button-sm"
                disabled={disabled}
                type="button"
                onClick={() => onRemove(entry.id)}
              >
                Remove
              </button>
            </div>

            <div className="blocked-time-grid">
              <label className="settings-field">
                <span>Label</span>
                <input
                  aria-label={`Blocked time label ${index + 1}`}
                  className="settings-input"
                  disabled={disabled}
                  type="text"
                  value={entry.label}
                  onChange={(event) => onChange(entry.id, { label: event.target.value })}
                />
              </label>

              <label className="settings-field">
                <span>Start</span>
                <input
                  aria-label={`Blocked time start ${index + 1}`}
                  className="settings-input"
                  disabled={disabled}
                  type="time"
                  value={entry.start}
                  onChange={(event) => onChange(entry.id, { start: event.target.value })}
                />
              </label>

              <label className="settings-field">
                <span>End</span>
                <input
                  aria-label={`Blocked time end ${index + 1}`}
                  className="settings-input"
                  disabled={disabled}
                  type="time"
                  value={entry.end}
                  onChange={(event) => onChange(entry.id, { end: event.target.value })}
                />
              </label>
            </div>

            <fieldset className="settings-fieldset">
              <legend>Days</legend>
              <div className="weekday-chip-row">
                {WEEKDAY_OPTIONS.map((day) => {
                  const checked = entry.days.includes(day.code)

                  return (
                    <label
                      className={`weekday-chip${checked ? ' is-selected' : ''}`}
                      key={`${entry.id}-${day.code}`}
                    >
                      <input
                        checked={checked}
                        disabled={disabled}
                        type="checkbox"
                        onChange={(event) => {
                          const nextDays = event.target.checked
                            ? [...entry.days, day.code]
                            : entry.days.filter((value) => value !== day.code)

                          onChange(entry.id, { days: nextDays })
                        }}
                      />
                      <span>{day.label}</span>
                    </label>
                  )
                })}
              </div>
            </fieldset>
          </article>
        ))}
      </div>

      {error ? <p className="settings-field-error">{error}</p> : null}
    </section>
  )
}

