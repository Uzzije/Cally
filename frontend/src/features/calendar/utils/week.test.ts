import { describe, expect, it } from 'vitest'

import {
  buildWeekOptions,
  getStartOfWeek,
} from './week'


describe('buildWeekOptions', () => {
  it('includes the visible week and surrounding weeks for jumping', () => {
    const weekStart = getStartOfWeek(new Date('2026-04-06T12:00:00Z'))

    const options = buildWeekOptions(weekStart)

    expect(options).toHaveLength(17)
    expect(options.some((option) => option.value === weekStart.toISOString())).toBe(true)
    expect(options.some((option) => option.label.includes('Apr 6'))).toBe(true)
  })
})
