import { startTransition, useEffect, useRef, useState } from 'react'

import { createSavedInsight } from '../../analytics/api/analyticsClient'
import type { ExecutionMode } from '../../settings/types'
import {
  approveActionProposal,
  createChatSession,
  fetchChatMessages,
  fetchChatSessions,
  fetchChatTurnStatus,
  rejectActionProposal,
  submitChatMessage,
} from '../api/chatClient'
import type {
  ActionCardAction,
  ChatMessage,
  ChatSessionSummary,
  EmailDraftBlock,
} from '../types'
import { ChatComposer } from './ChatComposer'
import { ChatSessionSwitcher } from './ChatSessionSwitcher'
import { ChatStatusLine } from './ChatStatusLine'
import { MessageList } from './MessageList'


const CHAT_TURN_POLL_INTERVAL_MS = 3000

type ChatWorkspaceProps = {
  activeTimeZone: string
  csrfToken: string
  executionMode: ExecutionMode | null
  isOpen: boolean
  isPreferencesLoading: boolean
  onRefreshMessageCredits: () => Promise<void>
  onBlockSuggestedTimes: (block: EmailDraftBlock) => void
  onCopyEmailDraft: (block: EmailDraftBlock) => Promise<void>
  onProposalExecuted: () => Promise<void>
}

export function ChatWorkspace({
  activeTimeZone,
  csrfToken,
  executionMode,
  isOpen,
  isPreferencesLoading,
  onRefreshMessageCredits,
  onBlockSuggestedTimes,
  onCopyEmailDraft,
  onProposalExecuted,
}: ChatWorkspaceProps) {
  const chatViewportRef = useRef<HTMLDivElement | null>(null)
  const pollingTimeoutsRef = useRef<number[]>([])
  const activeSessionIdRef = useRef<number | null>(null)
  const messagesRef = useRef<ChatMessage[]>([])
  const mountedRef = useRef(true)
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([])
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [chatError, setChatError] = useState<string | null>(null)
  const [activeProposalId, setActiveProposalId] = useState<string | null>(null)
  const [saveChartStates, setSaveChartStates] = useState<
    Record<
      string,
      {
        status: 'idle' | 'saving' | 'saved' | 'error'
        error?: string | null
      }
    >
  >({})
  const [isSessionsLoading, setIsSessionsLoading] = useState(true)
  const [isMessagesLoading, setIsMessagesLoading] = useState(false)
  const [isCreatingSession, setIsCreatingSession] = useState(false)
  const [isSubmittingMessage, setIsSubmittingMessage] = useState(false)

  const refreshSessions = async (nextActiveSessionId?: number | null) => {
    const response = await fetchChatSessions()
    setSessions(response.sessions)

    if (response.sessions.length === 0) {
      startTransition(() => setActiveSessionId(null))
      return response.sessions
    }

    const targetSessionId =
      nextActiveSessionId ??
      (response.sessions.some((session) => session.id === activeSessionId)
        ? activeSessionId
        : response.sessions[0].id)

    startTransition(() => setActiveSessionId(targetSessionId))
    return response.sessions
  }

  const clearPollingTimeouts = () => {
    pollingTimeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId))
    pollingTimeoutsRef.current = []
  }

  const buildFallbackAssistantMessage = (messageId: string, text: string): ChatMessage => ({
    id: messageId,
    role: 'assistant',
    created_at: new Date().toISOString(),
    content_blocks: [{ type: 'text', text }],
  })

  const replaceMessageById = (targetId: number | string, nextMessage: ChatMessage) => {
    setMessages((current) =>
      current.flatMap((message) => (message.id === targetId ? [nextMessage] : [message])),
    )
  }

  const patchProposalInMessages = (
    proposalId: string,
    updater: (currentAction: ActionCardAction) => ActionCardAction,
  ) => {
    setMessages((current) =>
      current.map((message) => ({
        ...message,
        content_blocks: message.content_blocks.map((block) => {
          if (block.type !== 'action_card') {
            return block
          }

          return {
            ...block,
            actions: block.actions.map((action) =>
              action.id === proposalId ? updater(action) : action,
            ),
          }
        }),
      })),
    )
  }

  const pollChatTurn = (options: {
    sessionId: number
    turnId: number
    pendingAssistantMessageId: string
    fallbackMessageId: string
  }) => {
    const poll = async () => {
      if (!mountedRef.current || activeSessionIdRef.current !== options.sessionId) {
        return
      }

      try {
        const response = await fetchChatTurnStatus(options.sessionId, options.turnId)
        if (!mountedRef.current || activeSessionIdRef.current !== options.sessionId) {
          return
        }

        if (response.turn.status === 'completed') {
          clearPollingTimeouts()
          replaceMessageById(
            options.pendingAssistantMessageId,
            response.assistant_message ??
              buildFallbackAssistantMessage(
                options.fallbackMessageId,
                'I couldn’t respond just now. Please try again.',
              ),
          )
          await refreshSessions(options.sessionId)
          return
        }

        if (response.turn.status === 'failed') {
          clearPollingTimeouts()
          replaceMessageById(
            options.pendingAssistantMessageId,
            response.assistant_message ??
              buildFallbackAssistantMessage(
                options.fallbackMessageId,
                'I couldn’t respond just now. Please try again.',
              ),
          )
          setChatError('We could not generate a reply right now.')
          await refreshSessions(options.sessionId)
          return
        }

        const timeoutId = window.setTimeout(() => {
          void poll()
        }, CHAT_TURN_POLL_INTERVAL_MS)
        pollingTimeoutsRef.current.push(timeoutId)
      } catch {
        clearPollingTimeouts()
        replaceMessageById(
          options.pendingAssistantMessageId,
          buildFallbackAssistantMessage(
            options.fallbackMessageId,
            'I couldn’t respond just now. Please try again.',
          ),
        )
        setChatError('We could not generate a reply right now.')
      }
    }

    void poll()
  }

  const createAndSelectSession = async () => {
    setIsCreatingSession(true)

    try {
      const createdSession = await createChatSession(csrfToken)
      const nextSessions = await refreshSessions(createdSession.id)

      if (!nextSessions.some((session) => session.id === createdSession.id)) {
        setSessions((current) => [createdSession, ...current])
      }

      setMessages([])
      setChatError(null)
      return createdSession.id
    } finally {
      setIsCreatingSession(false)
    }
  }

  useEffect(() => {
    mountedRef.current = true
    let cancelled = false

    const loadSessions = async () => {
      setIsSessionsLoading(true)
      setChatError(null)

      try {
        const response = await fetchChatSessions()
        if (cancelled) {
          return
        }

        setSessions(response.sessions)
        if (response.sessions.length === 0) {
          const createdSession = await createChatSession(csrfToken)
          if (cancelled) {
            return
          }
          setSessions([createdSession])
          startTransition(() => setActiveSessionId(createdSession.id))
        } else {
          startTransition(() => setActiveSessionId(response.sessions[0].id))
        }
      } catch {
        if (!cancelled) {
          setChatError('We could not load chat sessions right now.')
        }
      } finally {
        if (!cancelled) {
          setIsSessionsLoading(false)
        }
      }
    }

    void loadSessions()

    return () => {
      cancelled = true
      mountedRef.current = false
      clearPollingTimeouts()
    }
  }, [csrfToken])

  useEffect(() => {
    activeSessionIdRef.current = activeSessionId
    clearPollingTimeouts()
    let cancelled = false

    const loadMessages = async () => {
      if (!activeSessionId) {
        setMessages([])
        setIsMessagesLoading(false)
        return
      }

      setIsMessagesLoading(true)
      setChatError(null)

      try {
        const response = await fetchChatMessages(activeSessionId)
        if (!cancelled) {
          setMessages(response.messages)
        }
      } catch {
        if (!cancelled) {
          setChatError('We could not load this conversation.')
        }
      } finally {
        if (!cancelled) {
          setIsMessagesLoading(false)
        }
      }
    }

    void loadMessages()

    return () => {
      cancelled = true
    }
  }, [activeSessionId])

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  useEffect(() => {
    if (isMessagesLoading) {
      return
    }

    const viewport = chatViewportRef.current
    if (!viewport) {
      return
    }

    const scrollToLatestMessage = () => {
      if (typeof viewport.scrollTo === 'function') {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: 'auto',
        })
      }

      viewport.scrollTop = viewport.scrollHeight
    }

    const animationFrameId = window.requestAnimationFrame(scrollToLatestMessage)

    return () => {
      window.cancelAnimationFrame(animationFrameId)
    }
  }, [activeSessionId, isMessagesLoading, isOpen, messages])

  const handleCreateSession = async () => {
    setChatError(null)

    try {
      await createAndSelectSession()
    } catch {
      setChatError('We could not start a new conversation.')
    }
  }

  const handleSubmitMessage = async () => {
    const trimmedDraft = draft.trim()
    if (!trimmedDraft || isSubmittingMessage) {
      return
    }

    const createdAt = new Date().toISOString()
    const optimisticUserMessage: ChatMessage = {
      id: `pending-user-${createdAt}`,
      role: 'user',
      created_at: createdAt,
      content_blocks: [{ type: 'text', text: trimmedDraft }],
    }
    const pendingAssistantMessage: ChatMessage = {
      id: `pending-assistant-${createdAt}`,
      role: 'assistant',
      created_at: createdAt,
      pending: true,
      content_blocks: [{ type: 'status', text: 'Thinking…' }],
    }

    setChatError(null)
    setIsSubmittingMessage(true)
    setMessages((current) => [...current, optimisticUserMessage, pendingAssistantMessage])
    setDraft('')

    try {
      const targetSessionId = activeSessionId ?? (await createAndSelectSession())
      if (!targetSessionId) {
        throw new Error('Missing chat session')
      }

      const response = await submitChatMessage(targetSessionId, trimmedDraft, csrfToken)
      await onRefreshMessageCredits()
      replaceMessageById(optimisticUserMessage.id, response.user_message)
      pollChatTurn({
        sessionId: targetSessionId,
        turnId: response.turn.id,
        pendingAssistantMessageId: String(pendingAssistantMessage.id),
        fallbackMessageId: `error-assistant-${createdAt}`,
      })
    } catch {
      try {
        await onRefreshMessageCredits()
      } catch {
        // Keep the chat fallback path intact if the credit refresh fails too.
      }

      replaceMessageById(
        pendingAssistantMessage.id,
        buildFallbackAssistantMessage(
          `error-assistant-${createdAt}`,
          'I couldn’t respond just now. Please try again.',
        ),
      )
      setChatError('We could not generate a reply right now.')
    } finally {
      setIsSubmittingMessage(false)
    }
  }

  const findProposal = (proposalId: string) => {
    for (const message of messagesRef.current) {
      for (const block of message.content_blocks) {
        if (block.type !== 'action_card') {
          continue
        }

        const action = block.actions.find((candidate) => candidate.id === proposalId)
        if (action) {
          return action
        }
      }
    }

    return null
  }

  const handleApproveProposal = async (proposalId: string) => {
    if (!activeSessionId || activeProposalId) {
      return
    }

    const previousAction = findProposal(proposalId)
    if (!previousAction) {
      return
    }

    setChatError(null)
    setActiveProposalId(proposalId)
    patchProposalInMessages(proposalId, (current) => ({
      ...current,
      status: 'executing',
      status_detail: 'Creating the event on your primary calendar.',
    }))

    try {
      const proposal = await approveActionProposal(activeSessionId, proposalId, csrfToken)
      patchProposalInMessages(proposalId, () => proposal)
      if (proposal.status === 'executed') {
        await onProposalExecuted()
      }
    } catch (error) {
      patchProposalInMessages(proposalId, () => previousAction)
      setChatError(
        error instanceof Error ? error.message : 'We could not execute that proposal right now.',
      )
    } finally {
      setActiveProposalId(null)
    }
  }

  const handleRejectProposal = async (proposalId: string) => {
    if (!activeSessionId || activeProposalId) {
      return
    }

    setChatError(null)
    setActiveProposalId(proposalId)

    try {
      const proposal = await rejectActionProposal(activeSessionId, proposalId, csrfToken)
      patchProposalInMessages(proposalId, () => proposal)
    } catch (error) {
      setChatError(
        error instanceof Error ? error.message : 'We could not reject that proposal right now.',
      )
    } finally {
      setActiveProposalId(null)
    }
  }

  const handleSaveChart = async (messageId: number, blockIndex: number) => {
    const stateKey = `${messageId}:${blockIndex}`
    setSaveChartStates((current) => ({
      ...current,
      [stateKey]: {
        status: 'saving',
        error: null,
      },
    }))

    try {
      const savedInsight = await createSavedInsight(messageId, blockIndex, csrfToken)
      setSaveChartStates((current) => ({
        ...current,
        [stateKey]: {
          status: 'saved',
          error: savedInsight.replaced_existing
            ? 'Replaced your current saved insight. Upgrade to keep more.'
            : null,
        },
      }))
    } catch (error) {
      setSaveChartStates((current) => ({
        ...current,
        [stateKey]: {
          status: 'error',
          error: error instanceof Error ? error.message : 'Unable to save this insight right now.',
        },
      }))
    }
  }

  return (
    <aside className="paper-panel chat-panel">
      <header className="chat-panel-header">
        <div className="chat-panel-brand">
          <div className="chat-panel-mark" aria-hidden="true">
            <span className="brand-book chat-brand-book">
              <span />
              <span />
            </span>
          </div>
          <div>
            <p className="eyebrow">Assistant</p>
            <h2>Ask Cally</h2>
          </div>
        </div>
        <p className="chat-panel-copy">
          Ask grounded calendar questions and review suggested actions before anything changes.
        </p>
        <p className="chat-panel-timezone">Chat timezone: {activeTimeZone}</p>
      </header>

      <ChatSessionSwitcher
        activeSessionId={activeSessionId}
        isCreating={isCreatingSession}
        isLoading={isSessionsLoading}
        sessions={sessions}
        onCreateSession={handleCreateSession}
        onSelectSession={(sessionId) => {
          startTransition(() => setActiveSessionId(sessionId))
        }}
      />

      <ChatStatusLine text={chatError} tone="error" />

      <div className="chat-panel-body" ref={chatViewportRef}>
        <MessageList
          activeProposalId={activeProposalId}
          executionMode={executionMode}
          isLoading={isMessagesLoading}
          isPreferencesLoading={isPreferencesLoading}
          messages={messages}
          onBlockSuggestedTimes={onBlockSuggestedTimes}
          onCopyEmailDraft={onCopyEmailDraft}
          onApproveAction={handleApproveProposal}
          onRejectAction={handleRejectProposal}
          onSaveChart={handleSaveChart}
          saveChartStates={saveChartStates}
        />
      </div>

      <ChatComposer
        disabled={isSubmittingMessage}
        value={draft}
        onChange={setDraft}
        onSubmit={handleSubmitMessage}
      />
    </aside>
  )
}
