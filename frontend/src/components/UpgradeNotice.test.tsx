import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ComingSoonDialog, UpgradeNotice } from './UpgradeNotice'


describe('UpgradeNotice', () => {
  it('renders an upgrade notice with a CTA when provided', async () => {
    const onCta = vi.fn()

    render(
      <UpgradeNotice
        body="Save more insights with the expanded plan."
        ctaLabel="Ask About Upgrading"
        eyebrow="Upgrade"
        title="Save more than one insight"
        onCta={onCta}
      />,
    )

    expect(screen.getByText(/save more than one insight/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /ask about upgrading/i }))
    expect(onCta).toHaveBeenCalledTimes(1)
  })

  it('renders a dismissible coming-soon dialog', async () => {
    const onClose = vi.fn()

    render(
      <ComingSoonDialog
        ariaLabel="Upgrade coming soon"
        body="Expanded saved insights are on the roadmap."
        title="Expanded saved insights"
        onClose={onClose}
      />,
    )

    expect(screen.getByRole('dialog', { name: /upgrade coming soon/i })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /close upgrade notice/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
