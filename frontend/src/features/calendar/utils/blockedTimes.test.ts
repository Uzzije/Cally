import { describe, expect, it } from 'vitest'

import { expandBlockedTimesForWeek } from './blockedTimes'


describe('expandBlockedTimesForWeek', () => {
  it('expands recurring blocked times into visible week segments', () => {
    const segments = expandBlockedTimesForWeek({
      blockedTimes: [
        {
          id: 'workout-block',
          label: 'Workout',
          days: ['mon', 'wed'],
          start: '07:00',
          end: '08:30',
        },
      ],
      weekDays: [
        {
          key: '2026-04-06T00:00:00.000Z',
          date: new Date('2026-04-06T00:00:00.000Z'),
          dayLabel: 'Mon',
          dateLabel: 'Apr 6',
        },
        {
          key: '2026-04-07T00:00:00.000Z',
          date: new Date('2026-04-07T00:00:00.000Z'),
          dayLabel: 'Tue',
          dateLabel: 'Apr 7',
        },
        {
          key: '2026-04-08T00:00:00.000Z',
          date: new Date('2026-04-08T00:00:00.000Z'),
          dayLabel: 'Wed',
          dateLabel: 'Apr 8',
        },
      ],
      timeZone: 'UTC',
    })

    expect(segments).toHaveLength(2)
    expect(segments[0].dayKey).toBe('2026-04-06T00:00:00.000Z')
    expect(segments[0].label).toBe('Workout')
    expect(segments[0].top).toBeCloseTo(29.16, 1)
    expect(segments[0].height).toBeCloseTo(6.25, 1)
  })
})

