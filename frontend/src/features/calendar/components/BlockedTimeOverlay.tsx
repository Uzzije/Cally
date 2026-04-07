import type { BlockedTimeSegment } from '../utils/blockedTimes'


type BlockedTimeOverlayProps = {
  segments: BlockedTimeSegment[]
}

export function BlockedTimeOverlay({ segments }: BlockedTimeOverlayProps) {
  return (
    <>
      {segments.map((segment) => (
        <div
          aria-label={`Blocked time ${segment.label}`}
          className="calendar-blocked-time"
          key={segment.key}
          style={{
            top: `${segment.top}%`,
            height: `${segment.height}%`,
          }}
        >
          <span>{segment.label}</span>
        </div>
      ))}
    </>
  )
}
