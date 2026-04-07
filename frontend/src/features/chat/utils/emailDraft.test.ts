import { describe, expect, it, vi } from 'vitest'

import { buildEmailDraftClipboardText, extractTempBlockedTimesFromEmailDraft } from './emailDraft'


describe('emailDraft utils', () => {
  it('builds clipboard text from an email draft block', () => {
    const clipboardText = buildEmailDraftClipboardText({
      type: 'email_draft',
      to: ['joe@example.com'],
      cc: ['manager@example.com'],
      subject: 'Quick sync this week?',
      body: 'Hi Joe,\n\nCould we find 30 minutes this week?\n',
      status: 'draft',
      status_detail: 'Draft only. Not sent.',
    })

    expect(clipboardText).toContain('To: joe@example.com')
    expect(clipboardText).toContain('Cc: manager@example.com')
    expect(clipboardText).toContain('Subject: Quick sync this week?')
    expect(clipboardText).toContain('Could we find 30 minutes this week?')
  })

  it('extracts temporary blocked times from suggested bullet lines in the email body', () => {
    vi.setSystemTime(new Date('2026-04-06T10:00:00Z'))

    const entries = extractTempBlockedTimesFromEmailDraft({
      type: 'email_draft',
      to: ['joe@example.com'],
      cc: [],
      subject: '30-minute meeting next week',
      body:
        'Hi Joe,\n\n' +
        'A few times that work for me:\n\n' +
        '• Tue, Apr 14 — 2:00–2:30 PM ET\n' +
        '• Wed, Apr 15 — 3:00–3:30 PM ET\n',
      status: 'draft',
    })

    expect(entries).toHaveLength(2)
    expect(entries[0].date).toBe('2026-04-14')
    expect(entries[0].start).toBe('14:00')
    expect(entries[0].end).toBe('14:30')
    expect(entries[1].date).toBe('2026-04-15')
    expect(entries[1].start).toBe('15:00')
    expect(entries[1].end).toBe('15:30')
  })
})
