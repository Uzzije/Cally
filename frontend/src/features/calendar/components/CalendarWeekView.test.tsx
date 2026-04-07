import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CalendarWeekView } from './CalendarWeekView'
import { buildWeekDays, getStartOfWeek } from '../utils/week'


describe('CalendarWeekView', () => {
  it('renders the full seven-day week including saturday and sunday', () => {
    render(
      <CalendarWeekView
        blockedTimes={[]}
        events={[]}
        isLoading={false}
        selectedEventId={null}
        scrollTargetTop={0}
        timeZone="America/New_York"
        weekDays={buildWeekDays(getStartOfWeek(new Date('2026-04-01T12:00:00Z')))}
        onSelectEvent={() => {}}
      />,
    )

    expect(screen.getByText('Mon')).toBeInTheDocument()
    expect(screen.getByText('Tue')).toBeInTheDocument()
    expect(screen.getByText('Wed')).toBeInTheDocument()
    expect(screen.getByText('Thu')).toBeInTheDocument()
    expect(screen.getByText('Fri')).toBeInTheDocument()
    expect(screen.getByText('Sat')).toBeInTheDocument()
    expect(screen.getByText('Sun')).toBeInTheDocument()
  })

  it('renders event times using the selected display timezone', () => {
    render(
      <CalendarWeekView
        blockedTimes={[]}
        events={[
          {
            id: 1,
            google_event_id: 'event-1',
            title: 'Planning',
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
        ]}
        isLoading={false}
        selectedEventId={null}
        scrollTargetTop={0}
        timeZone="America/Los_Angeles"
        weekDays={buildWeekDays(getStartOfWeek(new Date('2026-04-06T12:00:00Z')))}
        onSelectEvent={() => {}}
      />,
    )

    expect(screen.getByText('7:00 AM - 8:00 AM')).toBeInTheDocument()
  })
})
