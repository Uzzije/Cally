import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SettingsPage } from './SettingsPage'


const settingsClient = vi.hoisted(() => ({
  deleteAccount: vi.fn(),
  fetchPreferences: vi.fn(),
  updatePreferences: vi.fn(),
}))

vi.mock('../api/settingsClient', () => settingsClient)

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    settingsClient.deleteAccount.mockResolvedValue({ success: true })
  })

  it('renders the saved display timezone and saves updates', async () => {
    settingsClient.fetchPreferences.mockResolvedValue({
      execution_mode: 'draft_only',
      display_timezone: 'America/New_York',
      blocked_times: [],
    })
    settingsClient.updatePreferences.mockImplementation(async (preferences) => preferences)

    render(<SettingsPage csrfToken="csrf-token" onAccountDeleted={vi.fn()} />)

    const timezoneSelect = (await screen.findByRole('combobox', {
      name: /calendar and chat timezone/i,
    })) as HTMLSelectElement

    expect(timezoneSelect.value).toBe('America/New_York')

    await userEvent.selectOptions(timezoneSelect, 'America/Los_Angeles')
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() => {
      expect(settingsClient.updatePreferences).toHaveBeenCalledWith(
        expect.objectContaining({
          display_timezone: 'America/Los_Angeles',
        }),
        'csrf-token',
      )
    })
  })

  it('lets the user fall back to the synced calendar timezone', async () => {
    settingsClient.fetchPreferences.mockResolvedValue({
      execution_mode: 'draft_only',
      display_timezone: 'America/New_York',
      blocked_times: [],
    })
    settingsClient.updatePreferences.mockImplementation(async (preferences) => preferences)

    render(<SettingsPage csrfToken="csrf-token" onAccountDeleted={vi.fn()} />)

    const timezoneSelect = (await screen.findByRole('combobox', {
      name: /calendar and chat timezone/i,
    })) as HTMLSelectElement

    await userEvent.selectOptions(timezoneSelect, '')
    await userEvent.click(screen.getByRole('button', { name: /save settings/i }))

    await waitFor(() => {
      expect(settingsClient.updatePreferences).toHaveBeenCalledWith(
        expect.objectContaining({
          display_timezone: null,
        }),
        'csrf-token',
      )
    })
  })
})
