import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function buildAuthenticatedSessionResponse() {
  return jsonResponse({
    authenticated: true,
    user: {
      id: 1,
      email: 'uzomaemuchay@gmail.com',
      display_name: 'Uzoma',
      avatar_url: null,
      has_google_account: true,
      onboarding_completed: true,
    },
  })
}

function buildReadySyncStatusResponse() {
  return jsonResponse({
    has_calendar: true,
    sync_state: 'ready',
    last_synced_at: '2026-04-04T14:30:00Z',
    is_stale: false,
  })
}

describe('Calendar workspace', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders login and redirects to Google when unauthenticated', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)

        if (url.endsWith('/api/v1/auth/csrf')) {
          return jsonResponse({ success: true })
        }

        if (url.endsWith('/api/v1/auth/me')) {
          return jsonResponse({ authenticated: false, user: null })
        }

        return new Response('Not found', { status: 404 })
      }),
    )

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    const signInLink = await screen.findByRole('link', {
      name: /sign in with google/i,
    })

    expect(signInLink.getAttribute('href')).toContain('/accounts/google/login/?process=login')
  })

  it('renders the authenticated calendar and chat workspace', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)

        if (url.endsWith('/api/v1/auth/csrf')) {
          return jsonResponse({ success: true })
        }

        if (url.endsWith('/api/v1/auth/me')) {
          return buildAuthenticatedSessionResponse()
        }

        if (url.endsWith('/api/v1/calendar/sync-status')) {
          return buildReadySyncStatusResponse()
        }

        if (url.includes('/api/v1/calendar/events?')) {
          return jsonResponse({
            calendar: {
              id: 1,
              name: 'Primary',
              is_primary: true,
              last_synced_at: '2026-04-04T14:30:00Z',
            },
            events: [
              {
                id: 101,
                google_event_id: 'event-1',
                title: 'Design Review',
                description: 'Weekly sync',
                start_time: '2026-04-01T14:00:00Z',
                end_time: '2026-04-01T15:00:00Z',
                timezone: 'America/New_York',
                location: 'Zoom',
                status: 'confirmed',
                attendees: [{ email: 'teammate@example.com' }],
                organizer_email: 'owner@example.com',
                is_all_day: false,
              },
            ],
          })
        }

        if (url.endsWith('/api/v1/chat/sessions')) {
          return jsonResponse({
            sessions: [
              {
                id: 1,
                title: 'Tomorrow planning',
                updated_at: '2026-04-05T15:00:00Z',
              },
            ],
          })
        }

        if (url.endsWith('/api/v1/chat/sessions/1/messages')) {
          return jsonResponse({
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
                    type: 'text',
                    text: 'You have one meeting tomorrow.',
                  },
                ],
              },
            ],
          })
        }

        return new Response('Not found', { status: 404 })
      }),
    )

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/^your workspace$/i)).toBeInTheDocument()
    expect(await screen.findByText(/design review/i)).toBeInTheDocument()
    expect(await screen.findByText(/you have one meeting tomorrow/i)).toBeInTheDocument()
    expect(await screen.findByText(/timezone: america\/new_york/i)).toBeInTheDocument()
  })

  it('requests a new event range when navigating to the next week', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/calendar/sync-status')) {
        return buildReadySyncStatusResponse()
      }

      if (url.includes('/api/v1/calendar/events?')) {
        return jsonResponse({
          calendar: {
            id: 1,
            name: 'Primary',
            is_primary: true,
            last_synced_at: '2026-04-04T14:30:00Z',
          },
          events: [],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions')) {
        return jsonResponse({
          sessions: [
            {
              id: 1,
              title: 'Tomorrow planning',
              updated_at: '2026-04-05T15:00:00Z',
            },
          ],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions/1/messages')) {
        return jsonResponse({
          session: {
            id: 1,
            title: 'Tomorrow planning',
            updated_at: '2026-04-05T15:00:00Z',
          },
          messages: [],
        })
      }

      return new Response('Not found', { status: 404 })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await screen.findByText(/^your workspace$/i)
    const initialEventCalls = fetchMock.mock.calls.filter(([input]) =>
      String(input).includes('/api/v1/calendar/events?'),
    )

    await userEvent.click(screen.getAllByRole('button', { name: /next week/i })[0])

    await waitFor(() => {
      const eventCalls = fetchMock.mock.calls.filter(([input]) =>
        String(input).includes('/api/v1/calendar/events?'),
      )
      expect(eventCalls.length).toBeGreaterThan(initialEventCalls.length)
    })
  })

  it('sends a message and renders the assistant reply', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/calendar/sync-status')) {
        return buildReadySyncStatusResponse()
      }

      if (url.includes('/api/v1/calendar/events?')) {
        return jsonResponse({
          calendar: {
            id: 1,
            name: 'Primary',
            is_primary: true,
            last_synced_at: '2026-04-04T14:30:00Z',
          },
          events: [],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions') && !init?.method) {
        return jsonResponse({
          sessions: [
            {
              id: 1,
              title: 'Tomorrow planning',
              updated_at: '2026-04-05T15:00:00Z',
            },
          ],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions/1/messages') && !init?.method) {
        return jsonResponse({
          session: {
            id: 1,
            title: 'Tomorrow planning',
            updated_at: '2026-04-05T15:00:00Z',
          },
          messages: [],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions/1/messages') && init?.method === 'POST') {
        await new Promise((resolve) => {
          setTimeout(resolve, 10)
        })

        return jsonResponse({
          user_message: {
            id: 10,
            role: 'user',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'text',
                text: 'What does tomorrow look like?',
              },
            ],
          },
          assistant_message: {
            id: 11,
            role: 'assistant',
            created_at: '2026-04-05T15:00:02Z',
            content_blocks: [
              {
                type: 'text',
                text: 'Tomorrow starts with a design review at 10 AM.',
              },
            ],
          },
        })
      }

      return new Response('Not found', { status: 404 })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await screen.findByText(/^conversation$/i)

    await userEvent.type(
      screen.getByRole('textbox', { name: /chat message/i }),
      'What does tomorrow look like?',
    )
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }))

    expect(screen.getByText(/what does tomorrow look like\?/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/assistant is thinking/i)).toBeInTheDocument()
    expect(await screen.findByText(/tomorrow starts with a design review at 10 am/i)).toBeInTheDocument()
  })

  it('switches sessions and loads the selected conversation history', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/calendar/sync-status')) {
        return buildReadySyncStatusResponse()
      }

      if (url.includes('/api/v1/calendar/events?')) {
        return jsonResponse({
          calendar: {
            id: 1,
            name: 'Primary',
            is_primary: true,
            last_synced_at: '2026-04-04T14:30:00Z',
          },
          events: [],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions')) {
        return jsonResponse({
          sessions: [
            {
              id: 1,
              title: 'Tomorrow planning',
              updated_at: '2026-04-05T15:00:00Z',
            },
            {
              id: 2,
              title: 'Design follow-up',
              updated_at: '2026-04-05T16:00:00Z',
            },
          ],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions/1/messages')) {
        return jsonResponse({
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
                  type: 'text',
                  text: 'You have one meeting tomorrow.',
                },
              ],
            },
          ],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions/2/messages')) {
        return jsonResponse({
          session: {
            id: 2,
            title: 'Design follow-up',
            updated_at: '2026-04-05T16:00:00Z',
          },
          messages: [
            {
              id: 2,
              role: 'assistant',
              created_at: '2026-04-05T16:00:00Z',
              content_blocks: [
                {
                  type: 'text',
                  text: 'The design review follow-up is Thursday at 2 PM.',
                },
              ],
            },
          ],
        })
      }

      return new Response('Not found', { status: 404 })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/you have one meeting tomorrow/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /design follow-up/i }))

    expect(
      await screen.findByText(/the design review follow-up is thursday at 2 pm/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/you have one meeting tomorrow/i)).not.toBeInTheDocument()
  })

  it('replaces the pending assistant bubble with an error reply when submission fails', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/calendar/sync-status')) {
        return buildReadySyncStatusResponse()
      }

      if (url.includes('/api/v1/calendar/events?')) {
        return jsonResponse({
          calendar: {
            id: 1,
            name: 'Primary',
            is_primary: true,
            last_synced_at: '2026-04-04T14:30:00Z',
          },
          events: [],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions') && !init?.method) {
        return jsonResponse({
          sessions: [
            {
              id: 1,
              title: 'Tomorrow planning',
              updated_at: '2026-04-05T15:00:00Z',
            },
          ],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions/1/messages') && !init?.method) {
        return jsonResponse({
          session: {
            id: 1,
            title: 'Tomorrow planning',
            updated_at: '2026-04-05T15:00:00Z',
          },
          messages: [],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions/1/messages') && init?.method === 'POST') {
        await new Promise((resolve) => {
          setTimeout(resolve, 10)
        })

        return new Response('Unable to respond', { status: 500 })
      }

      return new Response('Not found', { status: 404 })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    await screen.findByText(/^conversation$/i)

    await userEvent.type(
      screen.getByRole('textbox', { name: /chat message/i }),
      'What does tomorrow look like?',
    )
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }))

    expect(screen.getByLabelText(/assistant is thinking/i)).toBeInTheDocument()
    expect(
      await screen.findByText(/i couldn’t respond just now\. please try again\./i),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText(/assistant is thinking/i)).not.toBeInTheDocument()
    expect(
      screen.getByText(/we could not generate a reply right now\./i),
    ).toBeInTheDocument()
  })
})
