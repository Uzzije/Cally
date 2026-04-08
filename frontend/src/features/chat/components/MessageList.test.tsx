import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { MessageList } from './MessageList'


describe('MessageList', () => {
  it('renders an empty state when there are no messages', () => {
    render(<MessageList isLoading={false} messages={[]} />)

    expect(
      screen.getByText(/start the conversation with a calendar question/i),
    ).toBeInTheDocument()
  })

  it('renders clarification blocks', () => {
    render(
      <MessageList
        isLoading={false}
        messages={[
          {
            id: 1,
            role: 'assistant',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'clarification',
                text: 'Do you mean today or tomorrow?',
              },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByText(/do you mean today or tomorrow/i)).toBeInTheDocument()
  })

  it('renders a thinking animation for pending assistant messages', () => {
    render(
      <MessageList
        isLoading={false}
        messages={[
          {
            id: 'pending-assistant',
            role: 'assistant',
            pending: true,
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'text',
                text: 'Thinking…',
              },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByLabelText(/cally is thinking/i)).toBeInTheDocument()
  })

  it('renders action-card proposal blocks with review-only metadata', () => {
    render(
      <MessageList
        executionMode="confirm"
        isLoading={false}
        messages={[
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
        ]}
      />,
    )

    expect(screen.getByText(/meeting with joe/i)).toBeInTheDocument()
    expect(screen.getByText(/pending review/i)).toBeInTheDocument()
    expect(screen.getByText(/9:00 am-9:30 am/i)).toBeInTheDocument()
    expect(screen.getByText(/^joe$/i)).toBeInTheDocument()
    expect(screen.getByText(/rank 1/i)).toBeInTheDocument()
    expect(screen.getByText(/attendee availability checks are clear/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /approve/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reject/i })).toBeInTheDocument()
  })

  it('renders proposal and fallback blocks safely in the same conversation', () => {
    render(
      <MessageList
        isLoading={false}
        messages={[
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
                    },
                    status: 'pending',
                  },
                ],
              },
            ],
          },
          {
            id: 2,
            role: 'assistant',
            created_at: '2026-04-05T15:01:00Z',
            content_blocks: [
              {
                type: 'text',
                text: 'I need a specific day before I can suggest more options.',
              },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByText(/meeting with joe/i)).toBeInTheDocument()
    expect(
      screen.getByText(/i need a specific day before i can suggest more options/i),
    ).toBeInTheDocument()
  })

  it('renders email draft blocks with explicit non-sent state', () => {
    render(
      <MessageList
        isLoading={false}
        messages={[
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
                suggested_times: [],
                status: 'draft',
                status_detail: 'Draft only. Not sent.',
              },
            ],
          },
        ]}
      />,
    )

    const preview = screen.getByRole('article', { name: /email draft preview/i })

    expect(preview).toBeInTheDocument()
    expect(within(preview).getByText(/^to$/i)).toBeInTheDocument()
    expect(within(preview).getByText(/joe@example.com/i)).toBeInTheDocument()
    expect(within(preview).getByText(/^cc$/i)).toBeInTheDocument()
    expect(within(preview).getByText(/manager@example.com/i)).toBeInTheDocument()
    expect(screen.getAllByText(/quick sync this week/i)[0]).toBeInTheDocument()
    expect(screen.getByText(/draft only\. not sent\./i)).toBeInTheDocument()
    expect(screen.getByText(/could we find 30 minutes this week/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /copy email/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /block suggested times/i })).toBeDisabled()
    expect(
      screen.getByText(/this draft does not include suggested times to block yet/i),
    ).toBeInTheDocument()
  })

  it('renders email draft blocks safely alongside other assistant blocks', () => {
    render(
      <MessageList
        isLoading={false}
        messages={[
          {
            id: 1,
            role: 'assistant',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'text',
                text: 'I drafted an email you can review below.',
              },
              {
                type: 'email_draft',
                to: ['joe@example.com'],
                cc: [],
                subject: 'Quick sync this week?',
                body: 'Hi Joe,\n\nCould we find 30 minutes this week?\n',
                suggested_times: [],
                status: 'draft',
              },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByText(/i drafted an email you can review below/i)).toBeInTheDocument()
    expect(screen.getByRole('article', { name: /email draft preview/i })).toBeInTheDocument()
    expect(screen.getAllByText(/quick sync this week/i)[0]).toBeInTheDocument()
    expect(screen.getByText(/draft only\. not sent\./i)).toBeInTheDocument()
  })

  it('renders chart blocks safely alongside text blocks', () => {
    render(
      <MessageList
        isLoading={false}
        messages={[
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
                subtitle: 'Based on synced events grouped by weekday.',
                data: [
                  { label: 'Mon', value: 4 },
                  { label: 'Tue', value: 2 },
                ],
                save_enabled: true,
              },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByText(/6\.0 hours of meetings this week/i)).toBeInTheDocument()
    expect(screen.getByRole('article', { name: /meeting hours this week chart/i })).toBeInTheDocument()
    expect(screen.getByText(/based on synced events grouped by weekday/i)).toBeInTheDocument()
    expect(screen.getAllByText('Mon')[0]).toBeInTheDocument()
    expect(screen.getAllByText('Tue')[0]).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save insight/i })).toBeInTheDocument()
  })

  it('only shows the save affordance on eligible chart blocks and invokes save', async () => {
    const onSaveChart = vi.fn()

    render(
      <MessageList
        isLoading={false}
        messages={[
          {
            id: 1,
            role: 'assistant',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'chart',
                chart_type: 'bar',
                title: 'Meeting hours this week',
                data: [{ label: 'Mon', value: 4 }],
                save_enabled: true,
              },
              {
                type: 'chart',
                chart_type: 'bar',
                title: 'Unsaved chart',
                data: [{ label: 'Tue', value: 2 }],
              },
            ],
          },
        ]}
        onSaveChart={onSaveChart}
      />,
    )

    expect(screen.getByRole('button', { name: /save insight/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /save insight/i }))

    expect(onSaveChart).toHaveBeenCalledWith(1, 0)
  })

  it('invokes email draft actions', async () => {
    const onCopyEmailDraft = vi.fn()
    const onBlockSuggestedTimes = vi.fn()

    render(
      <MessageList
        isLoading={false}
        messages={[
          {
            id: 1,
            role: 'assistant',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'email_draft',
                to: ['joe@example.com'],
                cc: [],
                subject: 'Quick sync this week?',
                body: 'Hi Joe,\n\nA few times that work for me:\n',
                suggested_times: [
                  {
                    date: '2026-04-14',
                    start: '14:00',
                    end: '14:30',
                    timezone: 'America/New_York',
                  },
                ],
                status: 'draft',
              },
            ],
          },
        ]}
        onBlockSuggestedTimes={onBlockSuggestedTimes}
        onCopyEmailDraft={onCopyEmailDraft}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /copy email/i }))
    await userEvent.click(screen.getByRole('button', { name: /block suggested times/i }))

    expect(onCopyEmailDraft).toHaveBeenCalledTimes(1)
    expect(onBlockSuggestedTimes).toHaveBeenCalledTimes(1)
  })

  it('keeps block suggested times enabled when the draft includes structured suggested times', () => {
    render(
      <MessageList
        isLoading={false}
        messages={[
          {
            id: 1,
            role: 'assistant',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'email_draft',
                to: ['kayla@example.com'],
                cc: [],
                subject: 'Request to reschedule our meeting on April 9',
                body: 'Hi Kayla,\n\nWould any of these 30-minute slots work for you?\n',
                suggested_times: [
                  {
                    date: '2026-04-09',
                    start: '15:00',
                    end: '15:30',
                    timezone: 'America/New_York',
                  },
                  {
                    date: '2026-04-10',
                    start: '10:00',
                    end: '10:30',
                    timezone: 'America/New_York',
                  },
                ],
                status: 'draft',
              },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByRole('button', { name: /block suggested times/i })).toBeEnabled()
    expect(
      screen.queryByText(/this draft does not include suggested times to block yet/i),
    ).not.toBeInTheDocument()
  })

  it('disables approval in draft-only mode and shows a review-only note', () => {
    render(
      <MessageList
        executionMode="draft_only"
        isLoading={false}
        messages={[
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
                    },
                    status: 'pending',
                  },
                ],
              },
            ],
          },
        ]}
      />,
    )

    expect(screen.getByRole('button', { name: /approve/i })).toBeDisabled()
    expect(screen.getByText(/draft-only mode keeps this proposal review-only/i)).toBeInTheDocument()
  })

  it('invokes action callbacks for pending proposals', async () => {
    const onApproveAction = vi.fn()
    const onRejectAction = vi.fn()

    render(
      <MessageList
        executionMode="confirm"
        isLoading={false}
        messages={[
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
                    },
                    status: 'pending',
                  },
                ],
              },
            ],
          },
        ]}
        onApproveAction={onApproveAction}
        onRejectAction={onRejectAction}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /approve/i }))
    await userEvent.click(screen.getByRole('button', { name: /reject/i }))

    expect(onApproveAction).toHaveBeenCalledWith('proposal-1')
    expect(onRejectAction).toHaveBeenCalledWith('proposal-1')
  })
})
