import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AnalyticsDashboardPage } from './AnalyticsDashboardPage'


const analyticsClient = vi.hoisted(() => ({
  deleteSavedInsight: vi.fn(),
  fetchSavedInsights: vi.fn(),
  refreshSavedInsight: vi.fn(),
}))

vi.mock('../api/analyticsClient', () => analyticsClient)

const sampleInsight = {
  id: 'insight-1',
  title: 'Meeting hours this week',
  summary_text: 'You have 6.0 hours of meetings this week so far.',
  chart_payload: {
    type: 'chart' as const,
    chart_type: 'bar' as const,
    title: 'Meeting hours this week',
    subtitle: 'Based on synced events grouped by weekday.',
    data: [
      { label: 'Mon', value: 4 },
      { label: 'Tue', value: 2 },
    ],
  },
  created_at: '2026-04-05T15:00:00Z',
  last_refreshed_at: '2026-04-05T15:00:00Z',
}

const samplePolicy = {
  max_saved_insights: 1,
  current_count: 1,
  replaces_on_save: true,
  upgrade_message:
    'You can save one insight for now. Support for keeping more saved insights is coming soon.',
}

describe('AnalyticsDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders a loading state before saved insights arrive', () => {
    analyticsClient.fetchSavedInsights.mockReturnValue(new Promise(() => {}))

    render(<AnalyticsDashboardPage csrfToken="csrf-token" />)

    expect(screen.getByText(/loading saved insights/i)).toBeInTheDocument()
  })

  it('renders an empty state when there are no saved insights', async () => {
    analyticsClient.fetchSavedInsights.mockResolvedValue({ items: [], policy: samplePolicy })

    render(<AnalyticsDashboardPage csrfToken="csrf-token" />)

    expect(await screen.findByText(/no saved insights yet/i)).toBeInTheDocument()
    expect(screen.getByText(/save an eligible analytics chart from chat/i)).toBeInTheDocument()
  })

  it('renders saved insights and updates state after refresh and delete', async () => {
    analyticsClient.fetchSavedInsights.mockResolvedValue({ items: [sampleInsight], policy: samplePolicy })
    analyticsClient.refreshSavedInsight.mockResolvedValue({
      ...sampleInsight,
      summary_text: 'Updated summary',
      chart_payload: {
        ...sampleInsight.chart_payload,
        data: [{ label: 'Mon', value: 5 }],
      },
      last_refreshed_at: '2026-04-06T11:00:00Z',
    })
    analyticsClient.deleteSavedInsight.mockResolvedValue(undefined)

    render(<AnalyticsDashboardPage csrfToken="csrf-token" />)

    expect(await screen.findByRole('button', { name: /meeting hours this week/i })).toBeInTheDocument()
    expect(screen.queryByText(/you have 6\.0 hours of meetings/i)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /meeting hours this week/i }))
    expect(await screen.findByText(/you have 6\.0 hours of meetings/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /^refresh$/i }))
    expect(await screen.findByText(/updated summary/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /delete/i }))

    await waitFor(() => {
      expect(screen.getByText(/no saved insights yet/i)).toBeInTheDocument()
    })
  })

  it('renders an error state when dashboard loading fails', async () => {
    analyticsClient.fetchSavedInsights.mockRejectedValue(new Error('Unable to fetch saved insights'))

    render(<AnalyticsDashboardPage csrfToken="csrf-token" />)

    expect(await screen.findByText(/we couldn't load your dashboard/i)).toBeInTheDocument()
    expect(screen.getByText(/unable to fetch saved insights/i)).toBeInTheDocument()
  })

  it('keeps other insights collapsed until opened', async () => {
    analyticsClient.fetchSavedInsights.mockResolvedValue({
      items: [
        sampleInsight,
        {
          ...sampleInsight,
          id: 'insight-2',
          title: 'Busiest day',
          summary_text: 'Thursday was your busiest day.',
        },
      ],
      policy: samplePolicy,
    })

    render(<AnalyticsDashboardPage csrfToken="csrf-token" />)

    expect(await screen.findByRole('button', { name: /meeting hours this week/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /busiest day/i })).toBeInTheDocument()
    expect(screen.queryByText(/thursday was your busiest day/i)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /busiest day/i }))

    expect(await screen.findByText(/thursday was your busiest day/i)).toBeInTheDocument()
    expect(screen.queryByText(/you have 6\.0 hours of meetings/i)).not.toBeInTheDocument()
  })

  it('shows a coming-soon note when only one saved insight is available', async () => {
    analyticsClient.fetchSavedInsights.mockResolvedValue({ items: [sampleInsight], policy: samplePolicy })

    render(<AnalyticsDashboardPage csrfToken="csrf-token" />)

    expect(await screen.findByText(/more saved insights are coming soon/i)).toBeInTheDocument()
    expect(
      screen.getByText(/support for keeping more saved insights is coming soon/i),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /see what's coming/i }))
    expect(
      await screen.findByRole('dialog', { name: /saved insights update coming soon/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/^coming soon$/i)).toBeInTheDocument()
    expect(screen.getByText(/more saved insights/i)).toBeInTheDocument()
  })
})
