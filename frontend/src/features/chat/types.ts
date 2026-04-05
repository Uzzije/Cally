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

export type ChatContentBlock = TextBlock | ClarificationBlock | StatusBlock

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

export type ChatMessageHistoryResponse = {
  session: ChatSessionSummary
  messages: ChatMessage[]
}

export type ChatSubmitMessageResponse = {
  user_message: ChatMessage
  assistant_message: ChatMessage
}
