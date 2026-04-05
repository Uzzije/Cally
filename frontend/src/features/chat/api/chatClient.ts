import type {
  ChatMessageHistoryResponse,
  ChatSessionSummary,
  ChatSessionsResponse,
  ChatSubmitMessageResponse,
} from '../types'
import {
  parseChatMessageHistoryResponse,
  parseChatSessionResponse,
  parseChatSessionsResponse,
  parseChatSubmitMessageResponse,
} from '../utils/parsers'


const backendBaseUrl =
  import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000'

async function handleJsonResponse(response: Response, fallbackMessage: string) {
  if (!response.ok) {
    throw new Error(fallbackMessage)
  }

  return response.json()
}

export async function fetchChatSessions(): Promise<ChatSessionsResponse> {
  const response = await fetch(`${backendBaseUrl}/api/v1/chat/sessions`, {
    credentials: 'include',
  })

  return parseChatSessionsResponse(
    await handleJsonResponse(response, 'Unable to fetch chat sessions'),
  )
}

export async function createChatSession(csrfToken: string): Promise<ChatSessionSummary> {
  const response = await fetch(`${backendBaseUrl}/api/v1/chat/sessions`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'X-CSRFToken': csrfToken,
    },
  })

  return parseChatSessionResponse(
    await handleJsonResponse(response, 'Unable to create chat session'),
  )
}

export async function fetchChatMessages(
  sessionId: number,
): Promise<ChatMessageHistoryResponse> {
  const response = await fetch(
    `${backendBaseUrl}/api/v1/chat/sessions/${sessionId}/messages`,
    {
      credentials: 'include',
    },
  )

  return parseChatMessageHistoryResponse(
    await handleJsonResponse(response, 'Unable to fetch chat history'),
  )
}

export async function submitChatMessage(
  sessionId: number,
  content: string,
  csrfToken: string,
): Promise<ChatSubmitMessageResponse> {
  const response = await fetch(
    `${backendBaseUrl}/api/v1/chat/sessions/${sessionId}/messages`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ content }),
    },
  )

  return parseChatSubmitMessageResponse(
    await handleJsonResponse(response, 'Unable to submit chat message'),
  )
}

