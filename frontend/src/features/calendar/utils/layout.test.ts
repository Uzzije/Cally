import { describe, expect, it } from 'vitest'

import { getEventBlockStyle, getInitialCalendarScrollTop } from './layout'


describe('getEventBlockStyle', () => {
  it('calculates top and height percentages for timed events', () => {
    const style = getEventBlockStyle({
      startTime: '2026-04-06T14:00:00Z',
      endTime: '2026-04-06T15:30:00Z',
      timeZone: 'UTC',
    })

    expect(style.top).toBeCloseTo(58.33, 1)
    expect(style.height).toBeCloseTo(6.25, 1)
  })

  it('calculates an initial scroll offset near the earliest event', () => {
    const scrollTop = getInitialCalendarScrollTop([
      {
        id: 1,
        google_event_id: 'event-1',
        title: 'Standup',
        description: '',
        start_time: '2026-04-06T14:00:00Z',
        end_time: '2026-04-06T15:00:00Z',
        timezone: 'UTC',
        location: '',
        status: 'confirmed',
        attendees: [],
        organizer_email: 'owner@example.com',
        is_all_day: false,
      },
    ])

    expect(scrollTop).toBe(546)
  })

  it('keeps the default top position when the week has no events', () => {
    expect(getInitialCalendarScrollTop([])).toBe(0)
  })
})
