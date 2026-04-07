import type { ChartBlock } from '../chat/types'


export type SavedInsight = {
  id: string
  title: string
  summary_text: string
  chart_payload: ChartBlock
  created_at: string
  last_refreshed_at: string
  replaced_existing?: boolean
}

export type SavedInsightPolicy = {
  max_saved_insights: number
  current_count: number
  replaces_on_save: boolean
  upgrade_message: string
}

export type SavedInsightsResponse = {
  items: SavedInsight[]
  policy: SavedInsightPolicy
}
