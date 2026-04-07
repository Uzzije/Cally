import type { ChartBlock as ChartBlockType } from '../types'


const CHART_HEIGHT = 160
const BAR_WIDTH = 32
const BAR_GAP = 14
const LEFT_PADDING = 18
const TOP_PADDING = 14
const BOTTOM_PADDING = 28

export function ChartBlock({
  block,
  onSave,
  saveError,
  saveState = 'idle',
}: {
  block: ChartBlockType
  onSave?: () => void
  saveError?: string | null
  saveState?: 'idle' | 'saving' | 'saved' | 'error'
}) {
  const maxValue = Math.max(...block.data.map((point) => point.value), 1)
  const chartWidth =
    LEFT_PADDING * 2 + block.data.length * BAR_WIDTH + (block.data.length - 1) * BAR_GAP
  const plotHeight = CHART_HEIGHT - TOP_PADDING - BOTTOM_PADDING

  return (
    <article className="chart-block" aria-label={`${block.title} chart`}>
      <div className="chart-block-header">
        <div>
          <p className="chart-block-eyebrow">{block.chart_type} chart</p>
          <h3 className="chart-block-title">{block.title}</h3>
          {block.subtitle ? <p className="chart-block-subtitle">{block.subtitle}</p> : null}
        </div>
        {block.save_enabled ? (
          <div className="chart-block-actions">
            <button
              className="secondary-button button-sm"
              disabled={saveState === 'saving'}
              onClick={onSave}
              type="button"
            >
              {saveState === 'saving'
                ? 'Saving…'
                : saveState === 'saved'
                  ? 'Saved again'
                  : 'Save insight'}
            </button>
            {saveError ? <p className="chart-block-error">{saveError}</p> : null}
          </div>
        ) : null}
      </div>
      <svg
        className="chart-block-canvas"
        viewBox={`0 0 ${chartWidth} ${CHART_HEIGHT}`}
        role="img"
        aria-label={block.title}
      >
        <line
          className="chart-axis"
          x1={LEFT_PADDING}
          y1={CHART_HEIGHT - BOTTOM_PADDING}
          x2={chartWidth - LEFT_PADDING}
          y2={CHART_HEIGHT - BOTTOM_PADDING}
        />
        {block.data.map((point, index) => {
          const barHeight = (point.value / maxValue) * plotHeight
          const x = LEFT_PADDING + index * (BAR_WIDTH + BAR_GAP)
          const y = CHART_HEIGHT - BOTTOM_PADDING - barHeight

          return (
            <g key={`${point.label}-${index}`}>
              <rect
                className="chart-bar"
                x={x}
                y={y}
                width={BAR_WIDTH}
                height={barHeight}
                rx="8"
                ry="8"
              />
              <text className="chart-value" x={x + BAR_WIDTH / 2} y={y - 6} textAnchor="middle">
                {point.value}
              </text>
              <text
                className="chart-label"
                x={x + BAR_WIDTH / 2}
                y={CHART_HEIGHT - 8}
                textAnchor="middle"
              >
                {point.label}
              </text>
            </g>
          )
        })}
      </svg>
    </article>
  )
}
