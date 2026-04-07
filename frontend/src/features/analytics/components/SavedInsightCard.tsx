import { ChartBlock } from '../../chat/components/ChartBlock'
import type { SavedInsight } from '../types'


function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

export function SavedInsightCard({
  isOpen,
  insight,
  isDeleting,
  isRefreshing,
  onToggle,
  onDelete,
  onRefresh,
}: {
  isOpen: boolean
  insight: SavedInsight
  isDeleting: boolean
  isRefreshing: boolean
  onToggle: () => void
  onDelete: () => void
  onRefresh: () => void
}) {
  return (
    <article aria-label={insight.title} className={`saved-insight-card paper-panel${isOpen ? ' is-open' : ''}`}>
      <button
        aria-expanded={isOpen}
        className="saved-insight-toggle"
        onClick={onToggle}
        type="button"
      >
        <div className="saved-insight-toggle-copy">
          <p className="eyebrow">Saved insight</p>
          <h2>{insight.title}</h2>
          <p className="saved-insight-meta">Refreshed {formatTimestamp(insight.last_refreshed_at)}</p>
        </div>
        <span aria-hidden="true" className="saved-insight-chevron">
          {isOpen ? '−' : '+'}
        </span>
      </button>

      {isOpen ? (
        <div className="saved-insight-panel">
          <div className="saved-insight-actions">
            <button
              className="secondary-button button-sm"
              disabled={isRefreshing}
              onClick={onRefresh}
              type="button"
            >
              {isRefreshing ? 'Refreshing…' : 'Refresh'}
            </button>
            <button
              className="secondary-button button-sm"
              disabled={isDeleting}
              onClick={onDelete}
              type="button"
            >
              {isDeleting ? 'Deleting…' : 'Delete'}
            </button>
          </div>

          <p className="saved-insight-summary">{insight.summary_text}</p>
          <div className="saved-insight-chart-shell">
            <ChartBlock block={insight.chart_payload} />
          </div>
        </div>
      ) : null}
    </article>
  )
}
