import type { ExecutionMode } from '../settings/types'


export type ChatSessionSummary = {
  id: number
  title: string
  updated_at: string
}

export type TextBlock = {
  type: 'text'
  text: string
}

export type ClarificationBlock = {
  type: 'clarification'
  text: string
}

export type StatusBlock = {
  type: 'status'
  text: string
}

export type ActionCardActionDetails = {
  date: string
  time: string
  attendees: string[]
  rank?: number
  why?: string
}

export type ActionCardAction = {
  id: string
  action_type: 'create_event'
  summary: string
  details: ActionCardActionDetails
  status: 'pending' | 'approved' | 'rejected' | 'executing' | 'executed' | 'failed'
  status_detail?: string | null
  result?: {
    event_id?: number
    google_event_id?: string
  } | null
}

export type ActionCardBlock = {
  type: 'action_card'
  actions: ActionCardAction[]
}

export type EmailDraftSuggestedTime = {
  date: string
  start: string
  end: string
  timezone?: string
}

export type EmailDraftBlock = {
  type: 'email_draft'
  to: string[]
  cc?: string[]
  subject: string
  body: string
  suggested_times?: EmailDraftSuggestedTime[]
  status: 'draft'
  status_detail?: string
}

export type ChartDatum = {
  label: string
  value: number
}

export type ChartBlock = {
  type: 'chart'
  chart_type: 'bar' | 'line' | 'pie' | 'heatmap'
  title: string
  subtitle?: string
  data: ChartDatum[]
  save_enabled?: boolean
}

export type ChatContentBlock =
  | TextBlock
  | ClarificationBlock
  | StatusBlock
  | ActionCardBlock
  | ChartBlock
  | EmailDraftBlock

export type ChatMessage = {
  id: number | string
  role: 'user' | 'assistant'
  content_blocks: ChatContentBlock[]
  created_at: string
  pending?: boolean
}

export type ChatSessionsResponse = {
  sessions: ChatSessionSummary[]
}

export type MessageCreditStatus = {
  limit: number
  used: number
  remaining: number
  usage_date: string
}

export type ChatMessageHistoryResponse = {
  session: ChatSessionSummary
  messages: ChatMessage[]
}

export type ChatTurn = {
  id: number
  status: 'queued' | 'running' | 'completed' | 'failed'
  result_kind: 'answer' | 'clarification' | 'fallback' | 'error'
  scope_decision: 'in_scope' | 'greeting' | 'out_of_scope' | 'mutation_request' | 'ambiguous'
  failure_reason: string | null
  trace_events: Array<Record<string, unknown>>
  created_at: string
  completed_at: string | null
}

export type ChatSubmitAcceptedResponse = {
  user_message: ChatMessage
  turn: ChatTurn
}

export type ChatTurnStatusResponse = {
  turn: ChatTurn
  assistant_message: ChatMessage | null
}

export type ProposalActionAvailability = {
  executionMode: ExecutionMode | null
  isPreferencesLoading: boolean
}
