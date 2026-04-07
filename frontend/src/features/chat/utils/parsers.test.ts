import { describe, expect, it } from 'vitest'

import { parseActionProposalResponse, parseChatMessageHistoryResponse } from './parsers'


describe('chat parsers', () => {
  it('accepts action_card blocks in chat history payloads', () => {
    const payload = parseChatMessageHistoryResponse({
      session: {
        id: 1,
        title: 'Tomorrow planning',
        updated_at: '2026-04-05T15:00:00Z',
      },
      messages: [
        {
          id: 1,
          role: 'assistant',
          created_at: '2026-04-05T15:00:00Z',
          content_blocks: [
            {
              type: 'action_card',
              actions: [
                {
                  id: 'proposal-1',
                  action_type: 'create_event',
                  summary: 'Meeting with Joe',
                  details: {
                    date: 'Tue Apr 7',
                    time: '9:00 AM-9:30 AM',
                    attendees: ['Joe'],
                    rank: 1,
                    why: 'Protects your blocked-time focus windows. Attendee availability checks are clear.',
                  },
                  status: 'pending',
                },
              ],
            },
          ],
        },
      ],
    })

    expect(payload.messages[0].content_blocks[0].type).toBe('action_card')
  })

  it('rejects malformed action_card blocks', () => {
    expect(() =>
      parseChatMessageHistoryResponse({
        session: {
          id: 1,
          title: 'Tomorrow planning',
          updated_at: '2026-04-05T15:00:00Z',
        },
        messages: [
          {
            id: 1,
            role: 'assistant',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'action_card',
                actions: [
                  {
                    id: 'proposal-1',
                    action_type: 'create_event',
                    details: {
                      date: 'Tue Apr 7',
                      time: '9:00 AM-9:30 AM',
                    },
                    status: 'pending',
                  },
                ],
              },
            ],
          },
        ],
      }),
    ).toThrow(/invalid chat history payload/i)
  })

  it('accepts email_draft blocks in chat history payloads', () => {
    const payload = parseChatMessageHistoryResponse({
      session: {
        id: 1,
        title: 'Tomorrow planning',
        updated_at: '2026-04-05T15:00:00Z',
      },
      messages: [
        {
          id: 1,
          role: 'assistant',
          created_at: '2026-04-05T15:00:00Z',
          content_blocks: [
            {
              type: 'email_draft',
              to: ['joe@example.com'],
              cc: ['manager@example.com'],
              subject: 'Quick sync this week?',
              body: 'Hi Joe,\n\nCould we find 30 minutes this week?\n',
              status: 'draft',
              status_detail: 'Draft only. Not sent.',
            },
          ],
        },
      ],
    })

    expect(payload.messages[0].content_blocks[0].type).toBe('email_draft')
  })

  it('accepts chart blocks in chat history payloads', () => {
    const payload = parseChatMessageHistoryResponse({
      session: {
        id: 1,
        title: 'Analytics',
        updated_at: '2026-04-05T15:00:00Z',
      },
      messages: [
        {
          id: 1,
          role: 'assistant',
          created_at: '2026-04-05T15:00:00Z',
          content_blocks: [
            {
              type: 'text',
              text: 'You have 6.0 hours of meetings this week so far.',
            },
            {
              type: 'chart',
              chart_type: 'bar',
              title: 'Meeting hours this week',
              data: [
                { label: 'Mon', value: 4 },
                { label: 'Tue', value: 2 },
              ],
              save_enabled: true,
            },
          ],
        },
      ],
    })

    expect(payload.messages[0].content_blocks[1].type).toBe('chart')
  })

  it('rejects malformed chart blocks', () => {
    expect(() =>
      parseChatMessageHistoryResponse({
        session: {
          id: 1,
          title: 'Analytics',
          updated_at: '2026-04-05T15:00:00Z',
        },
        messages: [
          {
            id: 1,
            role: 'assistant',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'chart',
                chart_type: 'bar',
                title: 'Meeting hours this week',
                data: [{ label: '', value: 'four' }],
              },
            ],
          },
        ],
      }),
    ).toThrow(/invalid chat history payload/i)
  })

  it('rejects malformed email_draft blocks', () => {
    expect(() =>
      parseChatMessageHistoryResponse({
        session: {
          id: 1,
          title: 'Tomorrow planning',
          updated_at: '2026-04-05T15:00:00Z',
        },
        messages: [
          {
            id: 1,
            role: 'assistant',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'email_draft',
                to: [],
                subject: 'Quick sync this week?',
                body: 'Hi Joe',
                status: 'draft',
              },
            ],
          },
        ],
      }),
    ).toThrow(/invalid chat history payload/i)
  })

  it('accepts execution-state proposal payloads', () => {
    const proposal = parseActionProposalResponse({
      id: 'proposal-1',
      action_type: 'create_event',
      summary: 'Meeting with Joe',
      details: {
        date: 'Tue Apr 7',
        time: '9:00 AM-9:30 AM',
        attendees: ['joe@example.com'],
      },
      status: 'executed',
      status_detail: 'Added to your primary calendar.',
      result: {
        event_id: 7,
        google_event_id: 'google-event-7',
      },
    })

    expect(proposal.status).toBe('executed')
    expect(proposal.result?.google_event_id).toBe('google-event-7')
  })
})
