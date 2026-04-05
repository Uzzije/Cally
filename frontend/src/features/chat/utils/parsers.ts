import type {
  ChatContentBlock,
  ChatMessage,
  ChatMessageHistoryResponse,
  ChatSessionSummary,
  ChatSessionsResponse,
  ChatSubmitMessageResponse,
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

function isContentBlock(value: unknown): value is ChatContentBlock {
  return (
    isRecord(value) &&
    (value.type === 'text' || value.type === 'clarification' || value.type === 'status') &&
    typeof value.text === 'string'
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

export function parseChatSubmitMessageResponse(payload: unknown): ChatSubmitMessageResponse {
  if (
    !isRecord(payload) ||
    !isChatMessage(payload.user_message) ||
    !isChatMessage(payload.assistant_message)
  ) {
    throw new Error('Invalid chat submit payload')
  }

  return payload as ChatSubmitMessageResponse
}

