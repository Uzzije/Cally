import { describe, expect, it, vi } from 'vitest'

import {
  buildEmailDraftClipboardText,
  extractTempBlockedTimesFromEmailDraft,
  hasSuggestedTimesInEmailDraft,
} from './emailDraft'


describe('emailDraft utils', () => {
  it('builds clipboard text from an email draft block', () => {
    const clipboardText = buildEmailDraftClipboardText({
      type: 'email_draft',
      to: ['joe@example.com'],
      cc: ['manager@example.com'],
      subject: 'Quick sync this week?',
      body: 'Hi Joe,\n\nCould we find 30 minutes this week?\n',
      suggested_times: [],
      status: 'draft',
      status_detail: 'Draft only. Not sent.',
    })

    expect(clipboardText).toContain('To: joe@example.com')
    expect(clipboardText).toContain('Cc: manager@example.com')
    expect(clipboardText).toContain('Subject: Quick sync this week?')
    expect(clipboardText).toContain('Could we find 30 minutes this week?')
  })

  it('extracts temporary blocked times from structured suggested times', () => {
    vi.setSystemTime(new Date('2026-04-06T10:00:00Z'))

    const entries = extractTempBlockedTimesFromEmailDraft({
      type: 'email_draft',
      to: ['joe@example.com'],
      cc: [],
      subject: '30-minute meeting next week',
      body: 'Hi Joe,\n\nA few times that work for me:\n',
      suggested_times: [
        {
          date: '2026-04-14',
          start: '14:00',
          end: '14:30',
          timezone: 'America/New_York',
        },
        {
          date: '2026-04-15',
          start: '15:00',
          end: '15:30',
          timezone: 'America/New_York',
        },
      ],
      status: 'draft',
    })

    expect(entries).toHaveLength(2)
    expect(entries[0].date).toBe('2026-04-14')
    expect(entries[0].start).toBe('14:00')
    expect(entries[0].end).toBe('14:30')
    expect(entries[0].timezone).toBe('America/New_York')
    expect(entries[1].date).toBe('2026-04-15')
    expect(entries[1].start).toBe('15:00')
    expect(entries[1].end).toBe('15:30')
  })

  it('detects whether an email draft includes suggested times that can be blocked', () => {
    expect(
      hasSuggestedTimesInEmailDraft({
        suggested_times: [
          {
            date: '2026-04-14',
            start: '14:00',
            end: '14:30',
            timezone: 'America/New_York',
          },
        ],
      }),
    ).toBe(true)

    expect(
      hasSuggestedTimesInEmailDraft({
        suggested_times: [],
      }),
    ).toBe(false)
  })
})
