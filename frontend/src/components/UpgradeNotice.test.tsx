import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ComingSoonDialog, UpgradeNotice } from './UpgradeNotice'


describe('UpgradeNotice', () => {
  it('renders a coming-soon notice with a CTA when provided', async () => {
    const onCta = vi.fn()

    render(
      <UpgradeNotice
        body="Support for saving more insights is coming soon."
        ctaLabel="See What's Coming"
        eyebrow="Coming Soon"
        title="More saved insights are coming soon"
        onCta={onCta}
      />,
    )

    expect(screen.getByText(/more saved insights are coming soon/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /see what's coming/i }))
    expect(onCta).toHaveBeenCalledTimes(1)
  })

  it('renders a dismissible coming-soon dialog', async () => {
    const onClose = vi.fn()

    render(
      <ComingSoonDialog
        ariaLabel="Saved insights update coming soon"
        body="Expanded support for saved insights is on the roadmap."
        title="More saved insights"
        onClose={onClose}
      />,
    )

    expect(
      screen.getByRole('dialog', { name: /saved insights update coming soon/i }),
    ).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /close coming soon notice/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
