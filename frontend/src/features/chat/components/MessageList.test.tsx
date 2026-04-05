import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

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

    expect(screen.getByLabelText(/assistant is thinking/i)).toBeInTheDocument()
  })
})
