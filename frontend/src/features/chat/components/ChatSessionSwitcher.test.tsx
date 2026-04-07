import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ChatSessionSwitcher } from './ChatSessionSwitcher'

describe('ChatSessionSwitcher', () => {
  it('renders conversation history inside a closed accordion by default', () => {
    render(
      <ChatSessionSwitcher
        activeSessionId={1}
        isCreating={false}
        isLoading={false}
        onCreateSession={() => {}}
        onSelectSession={() => {}}
        sessions={[
          {
            id: 1,
            title: 'First conversation',
            updated_at: '2026-04-05T15:00:00Z',
          },
        ]}
      />,
    )

    const accordion = screen.getByText(/conversation history/i).closest('details')
    expect(accordion).not.toBeNull()
    expect(accordion).not.toHaveAttribute('open')
  })

  it('lets the user select a conversation using radio buttons', async () => {
    const onSelectSession = vi.fn()

    render(
      <ChatSessionSwitcher
        activeSessionId={1}
        isCreating={false}
        isLoading={false}
        onCreateSession={() => {}}
        onSelectSession={onSelectSession}
        sessions={[
          {
            id: 1,
            title: 'First conversation',
            updated_at: '2026-04-05T15:00:00Z',
          },
          {
            id: 2,
            title: 'Second conversation',
            updated_at: '2026-04-06T15:00:00Z',
          },
        ]}
      />,
    )

    await userEvent.click(screen.getByText(/conversation history/i))
    const accordion = screen.getByText(/conversation history/i).closest('details')
    await userEvent.click(screen.getByRole('radio', { name: /second conversation/i }))

    expect(onSelectSession).toHaveBeenCalledWith(2)
    expect(accordion).not.toBeNull()
    expect(accordion).not.toHaveAttribute('open')
  })
})
