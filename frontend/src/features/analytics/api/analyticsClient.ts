import type { SavedInsight, SavedInsightPolicy, SavedInsightsResponse } from '../types'


const backendBaseUrl =
  import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isChartBlock(value: unknown): value is SavedInsight['chart_payload'] {
  return (
    isRecord(value) &&
    value.type === 'chart' &&
    (value.chart_type === 'bar' ||
      value.chart_type === 'line' ||
      value.chart_type === 'pie' ||
      value.chart_type === 'heatmap') &&
    typeof value.title === 'string' &&
    value.title.length > 0 &&
    (value.subtitle === undefined || typeof value.subtitle === 'string') &&
    Array.isArray(value.data) &&
    value.data.every(
      (point) =>
        isRecord(point) &&
        typeof point.label === 'string' &&
        typeof point.value === 'number',
    )
  )
}

function isSavedInsight(value: unknown): value is SavedInsight {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.title === 'string' &&
    typeof value.summary_text === 'string' &&
    isChartBlock(value.chart_payload) &&
    typeof value.created_at === 'string' &&
    typeof value.last_refreshed_at === 'string' &&
    (value.replaced_existing === undefined || typeof value.replaced_existing === 'boolean')
  )
}

function isSavedInsightPolicy(value: unknown): value is SavedInsightPolicy {
  return (
    isRecord(value) &&
    typeof value.max_saved_insights === 'number' &&
    typeof value.current_count === 'number' &&
    typeof value.replaces_on_save === 'boolean' &&
    typeof value.upgrade_message === 'string'
  )
}

function parseSavedInsightsResponse(payload: unknown): SavedInsightsResponse {
  if (
    !isRecord(payload) ||
    !Array.isArray(payload.items) ||
    !payload.items.every(isSavedInsight) ||
    !isSavedInsightPolicy(payload.policy)
  ) {
    throw new Error('Invalid saved insights payload')
  }

  return payload as SavedInsightsResponse
}

function parseSavedInsightResponse(payload: unknown): SavedInsight {
  if (!isSavedInsight(payload)) {
    throw new Error('Invalid saved insight payload')
  }

  return payload
}

async function handleJsonResponse(response: Response, fallbackMessage: string) {
  if (!response.ok) {
    try {
      const payload = await response.json()
      if (payload && typeof payload.detail === 'string') {
        throw new Error(payload.detail)
      }
    } catch (error) {
      if (error instanceof Error && error.message !== '') {
        throw error
      }
    }

    throw new Error(fallbackMessage)
  }

  return response.json()
}

export async function fetchSavedInsights(): Promise<SavedInsightsResponse> {
  const response = await fetch(`${backendBaseUrl}/api/v1/analytics/saved-insights`, {
    credentials: 'include',
  })

  return parseSavedInsightsResponse(
    await handleJsonResponse(response, 'Unable to fetch saved insights'),
  )
}

export async function createSavedInsight(
  assistantMessageId: number,
  blockIndex: number,
  csrfToken: string,
): Promise<SavedInsight> {
  const response = await fetch(`${backendBaseUrl}/api/v1/analytics/saved-insights`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify({
      assistant_message_id: assistantMessageId,
      block_index: blockIndex,
    }),
  })

  return parseSavedInsightResponse(
    await handleJsonResponse(response, 'Unable to save this insight'),
  )
}

export async function refreshSavedInsight(
  insightId: string,
  csrfToken: string,
): Promise<SavedInsight> {
  const response = await fetch(
    `${backendBaseUrl}/api/v1/analytics/saved-insights/${insightId}/refresh`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRFToken': csrfToken,
      },
    },
  )

  return parseSavedInsightResponse(
    await handleJsonResponse(response, 'Unable to refresh this insight'),
  )
}

export async function deleteSavedInsight(
  insightId: string,
  csrfToken: string,
): Promise<void> {
  const response = await fetch(
    `${backendBaseUrl}/api/v1/analytics/saved-insights/${insightId}`,
    {
      method: 'DELETE',
      credentials: 'include',
      headers: {
        'X-CSRFToken': csrfToken,
      },
    },
  )

  await handleJsonResponse(response, 'Unable to delete this insight')
}
