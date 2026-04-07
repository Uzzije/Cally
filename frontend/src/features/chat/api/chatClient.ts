import type {
  ActionCardAction,
  ChatMessageHistoryResponse,
  MessageCreditStatus,
  ChatSessionSummary,
  ChatSubmitAcceptedResponse,
  ChatSessionsResponse,
  ChatTurnStatusResponse,
} from '../types'
import {
  parseChatMessageHistoryResponse,
  parseChatSessionResponse,
  parseChatSessionsResponse,
  parseChatSubmitAcceptedResponse,
  parseChatTurnStatusResponse,
  parseActionProposalResponse,
} from '../utils/parsers'


const backendBaseUrl =
  import.meta.env.VITE_BACKEND_BASE_URL ?? 'http://localhost:8000'

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

export async function fetchChatSessions(): Promise<ChatSessionsResponse> {
  const response = await fetch(`${backendBaseUrl}/api/v1/chat/sessions`, {
    credentials: 'include',
  })

  return parseChatSessionsResponse(
    await handleJsonResponse(response, 'Unable to fetch chat sessions'),
  )
}

export async function fetchChatCredits(): Promise<MessageCreditStatus> {
  const response = await fetch(`${backendBaseUrl}/api/v1/chat/credits`, {
    credentials: 'include',
  })

  return handleJsonResponse(response, 'Unable to fetch chat credits') as Promise<MessageCreditStatus>
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
): Promise<ChatSubmitAcceptedResponse> {
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

  return parseChatSubmitAcceptedResponse(
    await handleJsonResponse(response, 'Unable to submit chat message'),
  )
}

export async function fetchChatTurnStatus(
  sessionId: number,
  turnId: number,
): Promise<ChatTurnStatusResponse> {
  const response = await fetch(
    `${backendBaseUrl}/api/v1/chat/sessions/${sessionId}/turns/${turnId}`,
    {
      credentials: 'include',
    },
  )

  return parseChatTurnStatusResponse(
    await handleJsonResponse(response, 'Unable to fetch chat turn status'),
  )
}

export async function fetchActionProposal(
  sessionId: number,
  proposalId: string,
): Promise<ActionCardAction> {
  const response = await fetch(
    `${backendBaseUrl}/api/v1/chat/sessions/${sessionId}/proposals/${proposalId}`,
    {
      credentials: 'include',
    },
  )

  return parseActionProposalResponse(
    await handleJsonResponse(response, 'Unable to fetch proposal'),
  )
}

export async function approveActionProposal(
  sessionId: number,
  proposalId: string,
  csrfToken: string,
): Promise<ActionCardAction> {
  const response = await fetch(
    `${backendBaseUrl}/api/v1/chat/sessions/${sessionId}/proposals/${proposalId}/approve`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRFToken': csrfToken,
      },
    },
  )

  return parseActionProposalResponse(
    await handleJsonResponse(response, 'Unable to approve proposal'),
  )
}

export async function rejectActionProposal(
  sessionId: number,
  proposalId: string,
  csrfToken: string,
): Promise<ActionCardAction> {
  const response = await fetch(
    `${backendBaseUrl}/api/v1/chat/sessions/${sessionId}/proposals/${proposalId}/reject`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRFToken': csrfToken,
      },
    },
  )

  return parseActionProposalResponse(
    await handleJsonResponse(response, 'Unable to reject proposal'),
  )
}
