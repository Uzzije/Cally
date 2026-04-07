import type { TempBlockedTimeEntry } from '../types'


function formatTempBlockedDate(date: string) {
  const parsed = new Date(`${date}T12:00:00`)
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  }).format(parsed)
}

type TempBlockedTimesPageProps = {
  entries: TempBlockedTimeEntry[]
  onClearAll: () => void
  onRemove: (entryId: string) => void
}

export function TempBlockedTimesPage({
  entries,
  onClearAll,
  onRemove,
}: TempBlockedTimesPageProps) {
  return (
    <section className="paper-panel settings-page">
        <header className="settings-page-header">
          <div>
            <p className="eyebrow">Temp Blocked Times</p>
            <h1>Manage temporary holds</h1>
          </div>
          <p className="settings-page-copy">
            Keep candidate windows visible in calendar view without changing recurring blocked
            times.
          </p>
        </header>

        {entries.length === 0 ? (
          <div className="settings-empty-state">
            <p>No temporary holds.</p>
            <p>
              Use “Block suggested times” on an email draft to place a short hold on candidate
              slots.
            </p>
          </div>
        ) : (
          <div className="settings-stack">
            <section className="settings-section">
              <div className="settings-section-heading">
                <div>
                  <h2>Active holds</h2>
                  <p className="settings-section-copy">
                    One-hour holds created from draft suggestions.
                  </p>
                </div>
                <button className="secondary-button button-sm" onClick={onClearAll} type="button">
                  Clear all
                </button>
              </div>

              <div className="temp-blocked-times-list">
                {entries.map((entry) => (
                  <article className="temp-blocked-time-card" key={entry.id}>
                    <div>
                      <p className="temp-blocked-time-label">{entry.label}</p>
                      <p className="temp-blocked-time-meta">
                        {formatTempBlockedDate(entry.date)} · {entry.start}–{entry.end}
                      </p>
                    </div>
                    <button
                      className="secondary-button button-sm"
                      onClick={() => onRemove(entry.id)}
                      type="button"
                    >
                      Remove
                    </button>
                  </article>
                ))}
              </div>
            </section>
          </div>
        )}
    </section>
  )
}
