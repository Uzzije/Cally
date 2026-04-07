import type {
  ActionCardAction,
  ChatContentBlock,
  ChartBlock,
  EmailDraftBlock,
  ChatMessage,
  ChatMessageHistoryResponse,
  ChatSessionSummary,
  ChatSubmitAcceptedResponse,
  ChatSessionsResponse,
  ChatTurn,
  ChatTurnStatusResponse,
} from '../types'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isSessionSummary(value: unknown): value is ChatSessionSummary {
  return (
    isRecord(value) &&
    typeof value.id === 'number' &&
    typeof value.title === 'string' &&
    typeof value.updated_at === 'string'
  )
}

function isActionDetails(value: unknown): value is ActionCardAction['details'] {
  return (
    isRecord(value) &&
    typeof value.date === 'string' &&
    typeof value.time === 'string' &&
    Array.isArray(value.attendees) &&
    value.attendees.every((attendee) => typeof attendee === 'string') &&
    (value.rank === undefined || typeof value.rank === 'number') &&
    (value.why === undefined || typeof value.why === 'string')
  )
}

function isActionCardAction(value: unknown): value is ActionCardAction {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    value.action_type === 'create_event' &&
    typeof value.summary === 'string' &&
    isActionDetails(value.details) &&
    (value.status === 'pending' ||
      value.status === 'approved' ||
      value.status === 'rejected' ||
      value.status === 'executing' ||
      value.status === 'executed' ||
      value.status === 'failed') &&
    (value.status_detail === undefined ||
      value.status_detail === null ||
      typeof value.status_detail === 'string') &&
    (value.result === undefined ||
      value.result === null ||
      (isRecord(value.result) &&
        (value.result.event_id === undefined || typeof value.result.event_id === 'number') &&
        (value.result.google_event_id === undefined ||
          typeof value.result.google_event_id === 'string')))
  )
}

function isEmailDraftBlock(value: unknown): value is EmailDraftBlock {
  return (
    isRecord(value) &&
    value.type === 'email_draft' &&
    Array.isArray(value.to) &&
    value.to.length > 0 &&
    value.to.every((recipient) => typeof recipient === 'string' && recipient.length > 0) &&
    (value.cc === undefined ||
      (Array.isArray(value.cc) &&
        value.cc.every((recipient) => typeof recipient === 'string' && recipient.length > 0))) &&
    typeof value.subject === 'string' &&
    value.subject.length > 0 &&
    typeof value.body === 'string' &&
    value.body.length > 0 &&
    value.status === 'draft' &&
    (value.status_detail === undefined || typeof value.status_detail === 'string')
  )
}

function isChartBlock(value: unknown): value is ChartBlock {
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
    value.data.length > 0 &&
    value.data.every(
      (point) =>
        isRecord(point) &&
        typeof point.label === 'string' &&
        point.label.length > 0 &&
        typeof point.value === 'number',
    ) &&
    (value.save_enabled === undefined || typeof value.save_enabled === 'boolean')
  )
}

function isContentBlock(value: unknown): value is ChatContentBlock {
  return (
    isRecord(value) &&
    (((value.type === 'text' || value.type === 'clarification' || value.type === 'status') &&
      typeof value.text === 'string') ||
      (value.type === 'action_card' &&
        Array.isArray(value.actions) &&
        value.actions.every(isActionCardAction)) ||
      isChartBlock(value) ||
      isEmailDraftBlock(value))
  )
}

function isChatMessage(value: unknown): value is ChatMessage {
  return (
    isRecord(value) &&
    typeof value.id === 'number' &&
    (value.role === 'user' || value.role === 'assistant') &&
    Array.isArray(value.content_blocks) &&
    value.content_blocks.every(isContentBlock) &&
    typeof value.created_at === 'string'
  )
}

function isChatTurn(value: unknown): value is ChatTurn {
  return (
    isRecord(value) &&
    typeof value.id === 'number' &&
    typeof value.status === 'string' &&
    typeof value.result_kind === 'string' &&
    typeof value.scope_decision === 'string' &&
    (typeof value.failure_reason === 'string' || value.failure_reason === null) &&
    Array.isArray(value.trace_events) &&
    value.trace_events.every((event) => isRecord(event)) &&
    typeof value.created_at === 'string' &&
    (typeof value.completed_at === 'string' || value.completed_at === null)
  )
}

export function parseChatSessionsResponse(payload: unknown): ChatSessionsResponse {
  if (
    !isRecord(payload) ||
    !Array.isArray(payload.sessions) ||
    !payload.sessions.every(isSessionSummary)
  ) {
    throw new Error('Invalid chat sessions payload')
  }

  return payload as ChatSessionsResponse
}

export function parseChatSessionResponse(payload: unknown): ChatSessionSummary {
  if (!isSessionSummary(payload)) {
    throw new Error('Invalid chat session payload')
  }

  return payload
}

export function parseChatMessageHistoryResponse(payload: unknown): ChatMessageHistoryResponse {
  if (
    !isRecord(payload) ||
    !isSessionSummary(payload.session) ||
    !Array.isArray(payload.messages) ||
    !payload.messages.every(isChatMessage)
  ) {
    throw new Error('Invalid chat history payload')
  }

  return payload as ChatMessageHistoryResponse
}

export function parseChatSubmitAcceptedResponse(payload: unknown): ChatSubmitAcceptedResponse {
  if (
    !isRecord(payload) ||
    !isChatMessage(payload.user_message) ||
    !isChatTurn(payload.turn)
  ) {
    throw new Error('Invalid chat submit payload')
  }

  return payload as ChatSubmitAcceptedResponse
}

export function parseChatTurnStatusResponse(payload: unknown): ChatTurnStatusResponse {
  if (
    !isRecord(payload) ||
    !isChatTurn(payload.turn) ||
    !(payload.assistant_message === null || isChatMessage(payload.assistant_message))
  ) {
    throw new Error('Invalid chat turn status payload')
  }

  return payload as ChatTurnStatusResponse
}

export function parseActionProposalResponse(payload: unknown): ActionCardAction {
  if (!isActionCardAction(payload)) {
    throw new Error('Invalid action proposal payload')
  }

  return payload
}
