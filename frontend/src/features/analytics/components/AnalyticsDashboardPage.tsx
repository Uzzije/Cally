import { useEffect, useState } from 'react'

import { ComingSoonDialog, UpgradeNotice } from '../../../components/UpgradeNotice'
import {
  deleteSavedInsight,
  fetchSavedInsights,
  refreshSavedInsight,
} from '../api/analyticsClient'
import type { SavedInsight, SavedInsightPolicy } from '../types'
import { SavedInsightCard } from './SavedInsightCard'

const SAVED_INSIGHTS_NOTICE = {
  eyebrow: 'Coming Soon',
  title: 'More saved insights are coming soon',
  body: 'You can save one insight for now. Support for keeping more saved insights is coming soon.',
  ctaLabel: "See What's Coming",
} as const

const SAVED_INSIGHTS_DIALOG = {
  ariaLabel: 'Saved insights update coming soon',
  title: 'More saved insights',
  body: 'We are working on support for saving multiple insights and organizing them more easily.',
} as const


export function AnalyticsDashboardPage({ csrfToken }: { csrfToken: string }) {
  const [insights, setInsights] = useState<SavedInsight[]>([])
  const [savedInsightPolicy, setSavedInsightPolicy] = useState<SavedInsightPolicy | null>(null)
  const [showComingSoonPopup, setShowComingSoonPopup] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeInsightId, setActiveInsightId] = useState<string | null>(null)
  const [activeAction, setActiveAction] = useState<'refresh' | 'delete' | null>(null)
  const [openInsightId, setOpenInsightId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const loadInsights = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await fetchSavedInsights()
        if (!cancelled) {
          setInsights(response.items)
          setSavedInsightPolicy(response.policy)
        }
      } catch (nextError) {
        if (!cancelled) {
          setError(
            nextError instanceof Error
              ? nextError.message
              : 'Unable to load saved insights right now.',
          )
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadInsights()

    return () => {
      cancelled = true
    }
  }, [])

  const handleRefresh = async (insightId: string) => {
    setError(null)
    setActiveInsightId(insightId)
    setActiveAction('refresh')

    try {
      const refreshed = await refreshSavedInsight(insightId, csrfToken)
      setInsights((current) =>
        current.map((insight) => (insight.id === insightId ? refreshed : insight)),
      )
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : 'Unable to refresh this insight right now.',
      )
    } finally {
      setActiveInsightId(null)
      setActiveAction(null)
    }
  }

  const handleDelete = async (insightId: string) => {
    setError(null)
    setActiveInsightId(insightId)
    setActiveAction('delete')

    try {
      await deleteSavedInsight(insightId, csrfToken)
      setInsights((current) => current.filter((insight) => insight.id !== insightId))
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : 'Unable to delete this insight right now.',
      )
    } finally {
      setActiveInsightId(null)
      setActiveAction(null)
    }
  }

  if (isLoading) {
    return (
      <section className="analytics-dashboard-state paper-panel">
        <p className="eyebrow">Analytics</p>
        <h2>Loading saved insights…</h2>
        <p>Preparing your dashboard cards.</p>
      </section>
    )
  }

  if (error && insights.length === 0) {
    return (
      <section className="analytics-dashboard-state paper-panel">
        <p className="eyebrow">Analytics Error</p>
        <h2>We couldn&apos;t load your dashboard</h2>
        <p>{error}</p>
      </section>
    )
  }

  if (insights.length === 0) {
    return (
      <section className="analytics-dashboard-state paper-panel">
        <p className="eyebrow">Saved Insights</p>
        <h2>No saved insights yet</h2>
        <p>Save an eligible analytics chart from chat to build your dashboard.</p>
      </section>
    )
  }

  return (
    <>
      {error ? <p className="error-text">{error}</p> : null}
      {savedInsightPolicy?.replaces_on_save ? (
        <UpgradeNotice
          body={SAVED_INSIGHTS_NOTICE.body}
          className="analytics-upgrade-note paper-panel"
          ctaLabel={SAVED_INSIGHTS_NOTICE.ctaLabel}
          eyebrow={SAVED_INSIGHTS_NOTICE.eyebrow}
          title={SAVED_INSIGHTS_NOTICE.title}
          onCta={() => setShowComingSoonPopup(true)}
        />
      ) : null}
      <section className="saved-insight-grid">
        {insights.map((insight) => (
          <SavedInsightCard
            isOpen={openInsightId === insight.id}
            insight={insight}
            isDeleting={activeInsightId === insight.id && activeAction === 'delete'}
            isRefreshing={activeInsightId === insight.id && activeAction === 'refresh'}
            key={insight.id}
            onToggle={() =>
              setOpenInsightId((current) => (current === insight.id ? null : insight.id))
            }
            onDelete={() => void handleDelete(insight.id)}
            onRefresh={() => void handleRefresh(insight.id)}
          />
        ))}
      </section>
      {showComingSoonPopup ? (
        <ComingSoonDialog
          ariaLabel={SAVED_INSIGHTS_DIALOG.ariaLabel}
          body={SAVED_INSIGHTS_DIALOG.body}
          title={SAVED_INSIGHTS_DIALOG.title}
          onClose={() => setShowComingSoonPopup(false)}
        />
      ) : null}
    </>
  )
}
