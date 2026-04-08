import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
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

function buildReadySyncStatusResponse(overrides?: Record<string, unknown>) {
  return jsonResponse({
    has_calendar: true,
    sync_state: 'ready',
    last_synced_at: '2026-04-04T14:30:00Z',
    is_stale: false,
    ...overrides,
  })
}

function buildPreferencesResponse(overrides?: Record<string, unknown>) {
  return jsonResponse({
    execution_mode: 'draft_only',
    display_timezone: null,
    blocked_times: [],
    ...overrides,
  })
}

function buildChatCreditsResponse(overrides?: Record<string, unknown>) {
  return jsonResponse({
    limit: 10,
    used: 0,
    remaining: 10,
    usage_date: '2026-04-06',
    ...overrides,
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

  it('renders the auth error route copy when sign-in fails', async () => {
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
      <MemoryRouter initialEntries={['/auth/error']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/we couldn't complete sign in/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /return to login/i })).toHaveAttribute('href', '/')
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

        if (url.endsWith('/api/v1/chat/credits')) {
          return buildChatCreditsResponse()
        }

        if (url.endsWith('/api/v1/settings/preferences')) {
          return buildPreferencesResponse()
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
                start_time: '2026-04-07T14:00:00Z',
                end_time: '2026-04-07T15:00:00Z',
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
    expect(await screen.findByText(/^timezone: america\/new_york$/i)).toBeInTheDocument()
    expect(await screen.findByLabelText(/ai message usage/i)).toBeInTheDocument()
    expect(screen.getByText(/^ai messages$/i)).toBeInTheDocument()
    expect(screen.getByText(/^10 \/ 10$/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /open ask cally/i }))
    expect(screen.getByRole('button', { name: /close ask cally/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /close ai chat/i })).toBeInTheDocument()
    expect(document.querySelector('.calendar-workspace')).toHaveClass('is-chat-expanded')
    expect(await screen.findByText(/chat timezone: america\/new_york/i)).toBeInTheDocument()

    await userEvent.hover(screen.getByLabelText(/ai message usage/i))
    expect(
      await screen.findByText(/when you hit the daily limit, new chat replies pause until your limit resets/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/upgrade for more messages and a higher daily cap/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /design review/i }))
    expect(screen.getByRole('dialog', { name: /event details/i })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /close event details/i }))
    expect(screen.queryByRole('dialog', { name: /event details/i })).not.toBeInTheDocument()
  })

  it('shows the last sync time instead of freshness banner copy', async () => {
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

        if (url.endsWith('/api/v1/chat/credits')) {
          return buildChatCreditsResponse()
        }

        if (url.endsWith('/api/v1/settings/preferences')) {
          return buildPreferencesResponse({ display_timezone: 'America/New_York' })
        }

        if (url.endsWith('/api/v1/calendar/sync-status')) {
          return buildReadySyncStatusResponse({
            sync_state: 'stale',
            is_stale: true,
          })
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
      }),
    )

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/last synced: apr 4, 10:30 am/i)).toBeInTheDocument()
    expect(
      screen.queryByText(/data is visible, but freshness may be lagging/i),
    ).not.toBeInTheDocument()
  })

  it('shows a reconnect notice when Google Calendar needs reauthorization', async () => {
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

        if (url.endsWith('/api/v1/chat/credits')) {
          return buildChatCreditsResponse()
        }

        if (url.endsWith('/api/v1/settings/preferences')) {
          return buildPreferencesResponse()
        }

        if (url.endsWith('/api/v1/calendar/sync-status')) {
          return buildReadySyncStatusResponse({
            has_calendar: false,
            sync_state: 'not_started',
            last_synced_at: null,
          })
        }

        if (url.endsWith('/api/v1/calendar/sync')) {
          return jsonResponse(
            {
              detail: 'Stored Google credential could not be decrypted. Please reconnect Google Calendar.',
              code: 'google_reauth_required',
            },
            503,
          )
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
      }),
    )

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(
      await screen.findByRole('heading', { name: /google calendar needs to be reconnected/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /reconnect google calendar/i }),
    ).toHaveAttribute('href', expect.stringContaining('/accounts/google/login/?process=login'))
    expect(screen.getByRole('button', { name: /sync calendar/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /open ask cally/i })).toBeDisabled()
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

      if (url.endsWith('/api/v1/chat/credits')) {
        return buildChatCreditsResponse()
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse()
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

  it('requests a new event range when selecting a different week from the jump menu', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/chat/credits')) {
        return buildChatCreditsResponse()
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse()
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

    const weekSelect = screen.getByLabelText(/jump to week/i) as HTMLSelectElement
    const targetWeekValue = Array.from(weekSelect.options).find(
      (option) => option.value !== weekSelect.value,
    )?.value

    expect(targetWeekValue).toBeTruthy()

    await userEvent.selectOptions(weekSelect, targetWeekValue!)

    await waitFor(() => {
      const eventCalls = fetchMock.mock.calls.filter(([input]) =>
        String(input).includes('/api/v1/calendar/events?'),
      )
      expect(eventCalls.length).toBeGreaterThan(initialEventCalls.length)
    })
  })

  it('sends a message and renders the assistant reply', async () => {
    let creditFetchCount = 0
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/chat/credits')) {
        creditFetchCount += 1
        return buildChatCreditsResponse(
          creditFetchCount > 1
            ? {
                used: 1,
                remaining: 9,
              }
            : undefined,
        )
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse()
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
          turn: {
            id: 21,
            status: 'queued',
            result_kind: 'error',
            scope_decision: 'ambiguous',
            failure_reason: null,
            trace_events: [],
            created_at: '2026-04-05T15:00:00Z',
            completed_at: null,
          },
        }, 202)
      }

      if (url.endsWith('/api/v1/chat/sessions/1/turns/21')) {
        return jsonResponse({
          turn: {
            id: 21,
            status: 'completed',
            result_kind: 'answer',
            scope_decision: 'in_scope',
            failure_reason: null,
            trace_events: [],
            created_at: '2026-04-05T15:00:00Z',
            completed_at: '2026-04-05T15:00:02Z',
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

    await userEvent.click(await screen.findByRole('button', { name: /open ask cally/i }))
    await screen.findByRole('heading', { name: /^ask cally$/i })

    await userEvent.type(
      screen.getByRole('textbox', { name: /chat message/i }),
      'What does tomorrow look like?',
    )
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }))

    expect(screen.getByText(/what does tomorrow look like\?/i)).toBeInTheDocument()
    expect(await screen.findByText(/tomorrow starts with a design review at 10 am/i)).toBeInTheDocument()
    expect(await screen.findByText(/^9 \/ 10$/i)).toBeInTheDocument()
  })

  it('submits a chat message when pressing enter in the composer', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/chat/credits')) {
        return buildChatCreditsResponse()
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse()
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
          turn: {
            id: 21,
            status: 'queued',
            result_kind: 'error',
            scope_decision: 'ambiguous',
            failure_reason: null,
            trace_events: [],
            created_at: '2026-04-05T15:00:00Z',
            completed_at: null,
          },
        }, 202)
      }

      if (url.endsWith('/api/v1/chat/sessions/1/turns/21')) {
        return jsonResponse({
          turn: {
            id: 21,
            status: 'completed',
            result_kind: 'answer',
            scope_decision: 'in_scope',
            failure_reason: null,
            trace_events: [],
            created_at: '2026-04-05T15:00:00Z',
            completed_at: '2026-04-05T15:00:02Z',
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

    await userEvent.click(await screen.findByRole('button', { name: /open ask cally/i }))
    await screen.findByRole('heading', { name: /^ask cally$/i })
    await screen.findByText(/tomorrow planning/i)

    const composer = screen.getByRole('textbox', { name: /chat message/i })
    await userEvent.type(composer, 'What does tomorrow look like?{enter}')

    expect(screen.getByText(/what does tomorrow look like\?/i)).toBeInTheDocument()
    expect(
      await screen.findByText(/tomorrow starts with a design review at 10 am/i),
    ).toBeInTheDocument()
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

      if (url.endsWith('/api/v1/chat/credits')) {
        return buildChatCreditsResponse()
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse()
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
    const chatViewport = document.querySelector('.chat-panel-body') as HTMLDivElement | null
    expect(chatViewport).not.toBeNull()
    if (chatViewport) {
      Object.defineProperty(chatViewport, 'scrollHeight', {
        configurable: true,
        value: 640,
      })
      chatViewport.scrollTop = 0
    }

    await userEvent.click(screen.getByText(/conversation history/i))
    await userEvent.click(screen.getByRole('radio', { name: /design follow-up/i }))

    expect(
      await screen.findByText(/the design review follow-up is thursday at 2 pm/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/you have one meeting tomorrow/i)).not.toBeInTheDocument()
    expect(chatViewport?.scrollTop).toBe(640)
  })

  it('scrolls to the latest message when the AI chat panel is opened', async () => {
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

        if (url.endsWith('/api/v1/settings/preferences')) {
          return buildPreferencesResponse()
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

    await screen.findByText(/you have one meeting tomorrow/i)

    const chatViewport = document.querySelector('.chat-panel-body') as HTMLDivElement | null
    expect(chatViewport).not.toBeNull()
    if (chatViewport) {
      Object.defineProperty(chatViewport, 'scrollHeight', {
        configurable: true,
        value: 720,
      })
      chatViewport.scrollTop = 0
    }

    await userEvent.click(screen.getByRole('button', { name: /open ask cally/i }))

    await waitFor(() => {
      expect(chatViewport?.scrollTop).toBe(720)
    })
  })

  it('renders persisted action-card proposals from session history on load', async () => {
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

        if (url.endsWith('/api/v1/settings/preferences')) {
          return buildPreferencesResponse()
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
                        },
                        status: 'pending',
                      },
                    ],
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

    expect(await screen.findByText(/meeting with joe/i)).toBeInTheDocument()
    expect(await screen.findByText(/pending review/i)).toBeInTheDocument()
    expect(await screen.findByText(/9:00 am-9:30 am/i)).toBeInTheDocument()
  })

  it('deletes account from settings and returns to login state', async () => {
    let sessionChecks = 0
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        sessionChecks += 1
        if (sessionChecks === 1) {
          return buildAuthenticatedSessionResponse()
        }
        return jsonResponse({ authenticated: false, user: null })
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse()
      }

      if (url.endsWith('/api/v1/auth/delete-account') && init?.method === 'POST') {
        return jsonResponse({ success: true })
      }

      return new Response('Not found', { status: 404 })
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter initialEntries={['/settings']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/assistant memory and planning policy/i)).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/type delete to confirm/i), 'DELETE')
    await userEvent.click(screen.getByRole('button', { name: /^delete account$/i }))

    expect(
      await screen.findByRole('link', {
        name: /sign in with google/i,
      }),
    ).toBeInTheDocument()
  })

  it('approves a proposal, updates chat state, and refreshes the calendar workspace', async () => {
    let calendarEventsRequestCount = 0
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse({ execution_mode: 'confirm' })
      }

      if (url.endsWith('/api/v1/calendar/sync-status')) {
        return buildReadySyncStatusResponse()
      }

      if (url.includes('/api/v1/calendar/events?')) {
        calendarEventsRequestCount += 1
        return jsonResponse({
          calendar: {
            id: 1,
            name: 'Primary',
            is_primary: true,
            last_synced_at: '2026-04-04T14:30:00Z',
          },
          events:
            calendarEventsRequestCount > 1
              ? [
                  {
                    id: 501,
                    google_event_id: 'google-event-501',
                    title: 'Meeting with Joe',
                    description: '',
                    start_time: '2026-04-07T13:00:00Z',
                    end_time: '2026-04-07T13:30:00Z',
                    timezone: 'America/New_York',
                    location: '',
                    status: 'confirmed',
                    attendees: [],
                    organizer_email: 'owner@example.com',
                    is_all_day: false,
                  },
                ]
              : [],
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
          ],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions/1/proposals/proposal-1/approve')) {
        expect(init?.method).toBe('POST')
        return jsonResponse({
          id: 'proposal-1',
          action_type: 'create_event',
          summary: 'Meeting with Joe',
          details: {
            date: 'Tue Apr 7',
            time: '9:00 AM-9:30 AM',
            attendees: ['Joe'],
          },
          status: 'executed',
          status_detail: 'Added to your primary calendar.',
          result: {
            event_id: 501,
            google_event_id: 'google-event-501',
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

    await userEvent.click(await screen.findByRole('button', { name: /open ask cally/i }))
    await screen.findByRole('button', { name: /approve/i })
    await userEvent.click(screen.getByRole('button', { name: /approve/i }))

    expect(await screen.findByText(/added to calendar/i)).toBeInTheDocument()
    expect(await screen.findByText(/added to your primary calendar/i)).toBeInTheDocument()
    expect(await screen.findAllByText(/meeting with joe/i)).not.toHaveLength(0)

    await waitFor(() => {
      const calendarEventCalls = fetchMock.mock.calls.filter(([input]) =>
        String(input).includes('/api/v1/calendar/events?'),
      )
      expect(calendarEventCalls.length).toBeGreaterThan(1)
    })
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

      if (url.endsWith('/api/v1/chat/credits')) {
        return buildChatCreditsResponse()
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse()
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
          turn: {
            id: 31,
            status: 'queued',
            result_kind: 'error',
            scope_decision: 'ambiguous',
            failure_reason: null,
            trace_events: [],
            created_at: '2026-04-05T15:00:00Z',
            completed_at: null,
          },
        }, 202)
      }

      if (url.endsWith('/api/v1/chat/sessions/1/turns/31')) {
        return jsonResponse({
          turn: {
            id: 31,
            status: 'failed',
            result_kind: 'error',
            scope_decision: 'in_scope',
            failure_reason: 'provider_error',
            trace_events: [],
            created_at: '2026-04-05T15:00:00Z',
            completed_at: null,
          },
          assistant_message: {
            id: 12,
            role: 'assistant',
            created_at: '2026-04-05T15:00:02Z',
            content_blocks: [
              {
                type: 'text',
                text: 'I couldn’t respond just now. Please try again.',
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

    await screen.findByRole('heading', { name: /^ask cally$/i })
    await screen.findByText(/tomorrow planning/i)

    await userEvent.type(
      screen.getByRole('textbox', { name: /chat message/i }),
      'What does tomorrow look like?',
    )
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }))

    expect(
      await screen.findByText(/i couldn’t respond just now\. please try again\./i),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText(/cally is thinking/i)).not.toBeInTheDocument()
    expect(
      screen.getByText(/we could not generate a reply right now\./i),
    ).toBeInTheDocument()
  })

  it('renders a firm out-of-scope refusal after polling completes', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/chat/credits')) {
        return buildChatCreditsResponse()
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse()
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
        return jsonResponse({
          user_message: {
            id: 10,
            role: 'user',
            created_at: '2026-04-05T15:00:00Z',
            content_blocks: [
              {
                type: 'text',
                text: 'the US stock market',
              },
            ],
          },
          turn: {
            id: 41,
            status: 'queued',
            result_kind: 'error',
            scope_decision: 'ambiguous',
            failure_reason: null,
            trace_events: [],
            created_at: '2026-04-05T15:00:00Z',
            completed_at: null,
          },
        }, 202)
      }

      if (url.endsWith('/api/v1/chat/sessions/1/turns/41')) {
        return jsonResponse({
          turn: {
            id: 41,
            status: 'completed',
            result_kind: 'fallback',
            scope_decision: 'out_of_scope',
            failure_reason: null,
            trace_events: [],
            created_at: '2026-04-05T15:00:00Z',
            completed_at: '2026-04-05T15:00:02Z',
          },
          assistant_message: {
            id: 13,
            role: 'assistant',
            created_at: '2026-04-05T15:00:02Z',
            content_blocks: [
              {
                type: 'text',
                text: 'I only handle calendar and workspace questions in this environment. You can ask things like “What does tomorrow look like?”, “How busy am I on Friday?”, or “Find events with Alex.”',
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

    await screen.findByRole('heading', { name: /^ask cally$/i })

    await userEvent.type(
      screen.getByRole('textbox', { name: /chat message/i }),
      'the US stock market',
    )
    await userEvent.click(screen.getByRole('button', { name: /^send$/i }))

    expect(
      await screen.findByText(/i only handle calendar and workspace questions in this environment/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/find events with alex/i)).toBeInTheDocument()
  })

  it('renders blocked-time overlays from saved preferences in the workspace', async () => {
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

        if (url.endsWith('/api/v1/settings/preferences')) {
          return buildPreferencesResponse({
            blocked_times: [
              {
                id: 'workout-block',
                label: 'Morning workout',
                days: ['mon'],
                start: '07:00',
                end: '08:30',
              },
            ],
          })
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
      }),
    )

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/^your workspace$/i)).toBeInTheDocument()
    expect(await screen.findByLabelText(/blocked time morning workout/i)).toBeInTheDocument()
  })

  it('uses the saved display timezone in the workspace', async () => {
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

        if (url.endsWith('/api/v1/settings/preferences')) {
          return buildPreferencesResponse({
            display_timezone: 'America/Los_Angeles',
          })
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
            ],
          })
        }

        if (url.endsWith('/api/v1/chat/sessions')) {
          return jsonResponse({ sessions: [] })
        }

        return new Response('Not found', { status: 404 })
      }),
    )

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/^timezone: america\/los_angeles$/i)).toBeInTheDocument()
    expect(await screen.findByText('7:00 AM - 8:00 AM')).toBeInTheDocument()
  })

  it('saves settings and shows the updated overlay after returning to the workspace', async () => {
    let savedPreferences = {
      execution_mode: 'draft_only',
      display_timezone: null,
      blocked_times: [],
    }

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/settings/preferences') && !init?.method) {
        return buildPreferencesResponse(savedPreferences)
      }

      if (url.endsWith('/api/v1/settings/preferences') && init?.method === 'PUT') {
        savedPreferences = JSON.parse(String(init.body)) as typeof savedPreferences
        return buildPreferencesResponse(savedPreferences)
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
      <MemoryRouter initialEntries={['/settings']}>
        <App />
      </MemoryRouter>,
    )

    expect(
      await screen.findByRole('heading', { name: /assistant memory and planning policy/i }),
    ).toBeInTheDocument()

    await userEvent.click(screen.getByRole('radio', { name: /confirm first/i }))
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: /calendar and chat timezone/i }),
      'America/Los_Angeles',
    )
    await userEvent.click(screen.getByRole('button', { name: /add blocked time/i }))
    await userEvent.type(
      screen.getByRole('textbox', { name: /blocked time label 1/i }),
      'Morning workout',
    )
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    expect(
      await screen.findByText(/preferences saved\. the assistant will use these constraints/i),
    ).toBeInTheDocument()

    await userEvent.click(screen.getByRole('link', { name: /^workspace$/i }))

    expect(await screen.findByText(/^your workspace$/i)).toBeInTheDocument()
    expect(await screen.findByLabelText(/blocked time morning workout/i)).toBeInTheDocument()
    expect(savedPreferences.execution_mode).toBe('confirm')
    expect(savedPreferences.display_timezone).toBe('America/Los_Angeles')
  })

  it('saves an eligible analytics chart from chat', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)

      if (url.endsWith('/api/v1/auth/csrf')) {
        return jsonResponse({ success: true })
      }

      if (url.endsWith('/api/v1/auth/me')) {
        return buildAuthenticatedSessionResponse()
      }

      if (url.endsWith('/api/v1/settings/temp-blocked-times')) {
        return jsonResponse({ entries: [] })
      }

      if (url.endsWith('/api/v1/settings/preferences')) {
        return buildPreferencesResponse()
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
              title: 'Analytics chat',
              updated_at: '2026-04-05T15:00:00Z',
            },
          ],
        })
      }

      if (url.endsWith('/api/v1/chat/sessions/1/messages')) {
        return jsonResponse({
          session: {
            id: 1,
            title: 'Analytics chat',
            updated_at: '2026-04-05T15:00:00Z',
          },
          messages: [
            {
              id: 101,
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
      }

      if (url.endsWith('/api/v1/analytics/saved-insights')) {
        return jsonResponse({
          id: 'insight-1',
          title: 'Meeting hours this week',
          summary_text: 'You have 6.0 hours of meetings this week so far.',
          chart_payload: {
            type: 'chart',
            chart_type: 'bar',
            title: 'Meeting hours this week',
            data: [
              { label: 'Mon', value: 4 },
              { label: 'Tue', value: 2 },
            ],
          },
          created_at: '2026-04-05T15:00:00Z',
          last_refreshed_at: '2026-04-05T15:00:00Z',
          replaced_existing: true,
        }, 201)
      }

      return new Response('Not found', { status: 404 })
    })

    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    const saveButton = await screen.findByRole('button', { name: /save insight/i })
    await userEvent.click(saveButton)

    expect(await screen.findByRole('button', { name: /saved again/i })).toBeInTheDocument()
    expect(screen.getByText(/replaced your current saved insight/i)).toBeInTheDocument()
  })

  it('renders the analytics dashboard route from primary navigation', async () => {
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

        if (url.endsWith('/api/v1/settings/temp-blocked-times')) {
          return jsonResponse({ entries: [] })
        }

        if (url.endsWith('/api/v1/analytics/saved-insights')) {
          return jsonResponse({
            items: [
              {
                id: 'insight-1',
                title: 'Meeting hours this week',
                summary_text: 'You have 6.0 hours of meetings this week so far.',
                chart_payload: {
                  type: 'chart',
                  chart_type: 'bar',
                  title: 'Meeting hours this week',
                  data: [
                    { label: 'Mon', value: 4 },
                    { label: 'Tue', value: 2 },
                  ],
                },
                created_at: '2026-04-05T15:00:00Z',
                last_refreshed_at: '2026-04-05T15:00:00Z',
                replaced_existing: false,
              },
            ],
            policy: {
              max_saved_insights: 1,
              current_count: 1,
              replaces_on_save: true,
              upgrade_message:
                'You can save one insight for now. Support for keeping more saved insights is coming soon.',
            },
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

    await userEvent.click(await screen.findByRole('link', { name: /analytics/i }))

    expect(await screen.findByText(/saved insights dashboard/i)).toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: /meeting hours this week/i }))
    expect(await screen.findByText(/you have 6\.0 hours of meetings/i)).toBeInTheDocument()
  })

  it('renders the temp blocked times workspace route', async () => {
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

        if (url.endsWith('/api/v1/chat/credits')) {
          return buildChatCreditsResponse()
        }

        if (url.endsWith('/api/v1/settings/temp-blocked-times')) {
          return jsonResponse({
            entries: [
              {
                id: 'temp-1',
                label: 'Hold for Joe',
                date: '2026-04-07',
                start: '09:00',
                end: '10:00',
                source: 'email_draft',
                created_at: '2026-04-06T15:00:00Z',
              },
            ],
          })
        }

        return new Response('Not found', { status: 404 })
      }),
    )

    render(
      <MemoryRouter initialEntries={['/temp-blocked-times']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/^temporary holds$/i)).toBeInTheDocument()
    expect(await screen.findByText(/hold for joe/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument()
  })
})
