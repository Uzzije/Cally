import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  clearTempBlockedTimes,
  createTempBlockedTimes,
  deleteAccount,
  deleteTempBlockedTime,
  fetchPreferences,
  fetchTempBlockedTimes,
  updatePreferences,
} from './settingsClient'


function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('settingsClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fetches typed preference data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse({
          execution_mode: 'draft_only',
          display_timezone: null,
          blocked_times: [],
        })),
    )

    await expect(fetchPreferences()).resolves.toEqual({
      execution_mode: 'draft_only',
      display_timezone: null,
      blocked_times: [],
    })
  })

  it('surfaces validation errors on update', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse(
          {
            detail: 'Preferences payload is invalid.',
            errors: {
              blocked_times: ['Entry 1 start time must be earlier than end time.'],
            },
          },
          422,
        )),
    )

    await expect(
      updatePreferences(
        {
          execution_mode: 'draft_only',
          display_timezone: 'America/New_York',
          blocked_times: [
            {
              id: 'block-1',
              label: 'Bad block',
              days: ['mon'],
              start: '09:00',
              end: '08:00',
            },
          ],
        },
        'csrf-token',
      ),
    ).rejects.toMatchObject({
      message: 'Preferences payload is invalid.',
      fieldErrors: {
        blocked_times: ['Entry 1 start time must be earlier than end time.'],
      },
    })
  })

  it('fetches temporary blocked times', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse({
          entries: [
            {
              id: 'temp-1',
              label: 'Hold for meeting',
              date: '2026-04-08',
              start: '14:00',
              end: '14:30',
              timezone: 'America/New_York',
              source: 'email_draft',
              created_at: '2026-04-06T12:00:00Z',
              expires_at: '2026-04-06T13:00:00Z',
            },
          ],
        })),
    )

    await expect(fetchTempBlockedTimes()).resolves.toEqual({
      entries: [
        {
          id: 'temp-1',
          label: 'Hold for meeting',
          date: '2026-04-08',
          start: '14:00',
          end: '14:30',
          timezone: 'America/New_York',
          source: 'email_draft',
          created_at: '2026-04-06T12:00:00Z',
          expires_at: '2026-04-06T13:00:00Z',
        },
      ],
    })
  })

  it('creates temporary blocked times with csrf protection', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ entries: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      createTempBlockedTimes(
        {
          timezone: 'America/New_York',
          entries: [
            {
              label: 'Hold for meeting',
              date: '2026-04-08',
              start: '14:00',
              end: '14:30',
              source: 'email_draft',
            },
          ],
        },
        'csrf-token',
      ),
    ).resolves.toEqual({ entries: [] })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/settings/temp-blocked-times'),
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-CSRFToken': 'csrf-token',
        }),
      }),
    )
  })

  it('deletes one temporary blocked time with csrf protection', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ entries: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(deleteTempBlockedTime('temp-1', 'csrf-token')).resolves.toEqual({ entries: [] })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/settings/temp-blocked-times/temp-1'),
      expect.objectContaining({
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'X-CSRFToken': 'csrf-token',
        },
      }),
    )
  })

  it('clears temporary blocked times with csrf protection', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ entries: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(clearTempBlockedTimes('csrf-token')).resolves.toEqual({ entries: [] })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/settings/temp-blocked-times'),
      expect.objectContaining({
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'X-CSRFToken': 'csrf-token',
        },
      }),
    )
  })

  it('deletes account with csrf protection', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ success: true }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(deleteAccount('csrf-token')).resolves.toEqual({ success: true })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/delete-account'),
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRFToken': 'csrf-token',
        },
      }),
    )
  })
})
