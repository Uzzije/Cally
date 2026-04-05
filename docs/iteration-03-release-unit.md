# Iteration 03 Release Unit

**Project:** Cal Assistant
**Release theme:** Conversational calendar understanding
**Status:** Proposed third releasable slice

**Product specification:** This release is the first vertical slice of the assistant described in [product-spec.md §7 Agent Design](product-spec.md#7-agent-design) (GAME loop, tool boundaries, and execution-state model). Iteration 3 implements only the **read-only** path—memory and environment steps that use synced calendar data and **no** mutating tools—while staying consistent with that design so later iterations can add proposals, execution modes, and the full tool surface without rework.

## 1. Recommendation

The next release unit should be:

**read-only chat workspace + persisted chat sessions + basic natural-language calendar Q&A over synced data**

This is the right third slice because Iteration 02 already proved the synced calendar foundation. The next highest-value capability is letting the user ask useful questions about that data without yet introducing mutation risk.

This follows sound iterative delivery principles:

- **thin vertical slices**
- **highest-value next capability**
- **read-before-write progression**
- **separation of concerns across chat, retrieval, and orchestration**

It is also the smallest slice that proves the product’s core assistant promise: the app is not only a calendar viewer, but a place where synced schedule data can be queried conversationally—matching the **“Simple query → respond directly”** branch of the GAME loop in [§7.1](product-spec.md#71-game-loop-goal-action-memory-environment) and the read-only tools in [§7.4](product-spec.md#74-agent-tools) (`get_events`, `search_events`, and related retrieval), before side-effect tools and execution states in [§7.3](product-spec.md#73-execution-states) come into play.

---

## 2. Iteration Goal

Ship the smallest production-credible version of Cal Assistant where an authenticated user can:

1. open the main workspace with calendar and chat together
2. start a chat session
3. ask a basic scheduling or calendar-awareness question
4. receive a grounded assistant answer based on synced Postgres calendar data
5. revisit persisted messages in the same session
6. switch between recent chat sessions
7. understand loading, failure, and unsupported-question states clearly

This is enough to release as an internal alpha that demonstrates the first true assistant loop without yet allowing calendar mutations, email sending, or approval workflows.

---

## 3. What Is In Scope

### Frontend

- main workspace composition with calendar + chat
- chat panel or chat workspace shell for authenticated users
- message list with persisted history
- composer for submitting user questions
- recent session list or switcher
- loading, empty, failed, and unsupported-query states
- calm assistant status messaging while a response is being generated

### Backend

- chat session persistence
- message persistence
- read-only chat API contracts
- assistant orchestration service for basic calendar Q&A, shaped to align with [Agent Design](product-spec.md#7-agent-design) (Agno orchestration, tool registration, and the read-only subset of [§7.4 Agent Tools](product-spec.md#74-agent-tools))
- read-only calendar retrieval tools over synced Postgres data
- session ownership and authenticated access enforcement

### Data

- `ChatSession` records per user
- `Message` records for user and assistant turns
- structured content blocks limited to what this release needs
- minimal tool execution metadata if needed for observability

---

## 4. What Is Out of Scope

- calendar create, update, or delete actions
- Gmail draft or send actions
- approval cards and execution workflows
- blocked-time preference editing
- advanced analytics and text-to-SQL charts
- multi-calendar management
- streaming SSE if a non-streaming request/response implementation is simpler for this release
- autonomous multi-step agent planning beyond basic read-only Q&A

Keeping these out preserves a clean slice and avoids mixing read-only assistant understanding with side-effect risk too early.

---

## 5. User Story for Release 3

**As an authenticated user, I want to ask questions about my calendar in a chat workspace and get grounded answers, so I can start using the app as an assistant instead of only as a calendar viewer.**

---

## 6. User Experience Flow

```text
User signs in
  -> App opens calendar workspace
  -> Chat panel is available beside or alongside the calendar
  -> User starts a new session or opens an existing one
  -> User asks a calendar question
  -> Backend loads session context and synced calendar data
  -> Read-only assistant service generates a grounded answer
  -> Assistant response is persisted and displayed
  -> User can continue the thread or return to it later
```

---

## 7. Success Criteria

This iteration is done when:

- a signed-in user can create and revisit chat sessions
- user and assistant messages are persisted correctly
- the assistant can answer basic calendar questions from synced Postgres data
- chat access is scoped strictly to the authenticated user’s own sessions and calendar data
- the UI handles loading, empty, unsupported, and failure states clearly
- the main workspace supports both calendar visibility and chat interaction without feeling bolted together
- core chat and read-only assistant flows are covered by tests

---

## 8. Proposed Architecture Slice

Orchestration should follow the product’s agent model: conversation history plus synced calendar state feed the assistant turn ([§7.1 GAME loop](product-spec.md#71-game-loop-goal-action-memory-environment)), with clarifying behavior ([§7.2](product-spec.md#72-clarification-behavior)) allowed where useful, but **no** transitions into PROPOSING / EXECUTING for mutating work until a future release ([§7.3](product-spec.md#73-execution-states)).

## 8.1 Frontend components

```text
CalendarChatPage
  -> CalendarWorkspace
  -> ChatWorkspace
       -> ChatSessionSwitcher
       -> MessageList
       -> MessageBlockRenderer
       -> ChatComposer
       -> ChatStatusLine
```

### Frontend responsibilities

- keep calendar rendering and chat orchestration as separate feature areas
- fetch chat sessions and messages through typed domain clients
- submit user prompts and render structured assistant responses
- preserve session-local UI state without duplicating server truth
- keep layout responsive and aligned with Chronicle Modern

## 8.2 Backend components

```text
chat app
  -> chat session model
  -> message model
  -> chat router
  -> chat session service
  -> chat message service
  -> read-only assistant orchestration service
  -> calendar retrieval/query adapters
```

### Backend responsibilities

- persist sessions and messages
- validate session ownership
- coordinate a read-only assistant turn
- retrieve synced calendar context through narrow interfaces
- return frontend-shaped message DTOs without leaking ORM models or LLM/provider concerns into routers

This keeps responsibilities aligned with SRP and supports later evolution toward the full tool list and execution semantics in [§7.4–§7.5](product-spec.md#74-agent-tools) without overcommitting now.

---

## 9. Suggested Backend Contract

### `GET /api/v1/chat/sessions`

Purpose:

- return recent chat sessions for the authenticated user

Example response:

```json
{
  "sessions": [
    {
      "id": "uuid",
      "title": "Tomorrow planning",
      "updated_at": "2026-04-05T15:00:00Z"
    }
  ]
}
```

### `POST /api/v1/chat/sessions`

Purpose:

- create a new chat session for the authenticated user

Example response:

```json
{
  "id": "uuid",
  "title": "New conversation",
  "updated_at": "2026-04-05T15:00:00Z"
}
```

### `GET /api/v1/chat/sessions/{session_id}/messages`

Purpose:

- return persisted message history for one authenticated user-owned session

Example response:

```json
{
  "session": {
    "id": "uuid",
    "title": "Tomorrow planning"
  },
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content_blocks": [
        {
          "type": "text",
          "text": "What does tomorrow look like?"
        }
      ],
      "created_at": "2026-04-05T15:00:00Z"
    }
  ]
}
```

### `POST /api/v1/chat/sessions/{session_id}/messages`

Purpose:

- persist a user message, run a read-only assistant turn, and return the assistant response

Example response:

```json
{
  "user_message": {
    "id": "uuid",
    "role": "user",
    "content_blocks": [
      {
        "type": "text",
        "text": "What does tomorrow look like?"
      }
    ],
    "created_at": "2026-04-05T15:00:00Z"
  },
  "assistant_message": {
    "id": "uuid",
    "role": "assistant",
    "content_blocks": [
      {
        "type": "text",
        "text": "Tomorrow you have 3 meetings, with your first at 9:30 AM and a free block from 1 PM to 3 PM."
      }
    ],
    "created_at": "2026-04-05T15:00:02Z"
  }
}
```

For this iteration, a synchronous request/response contract is acceptable if it keeps the slice smaller and more testable. Streaming can follow in a later release.

---

## 10. Suggested Data Model Additions

### `ChatSession`

- `id`
- `user_id`
- `title`
- `created_at`
- `updated_at`

Recommended constraints:

- index on `(user_id, updated_at)`

### `Message`

- `id`
- `session_id`
- `role`
- `content_blocks`
- `tool_calls`
- `created_at`

Recommended constraints:

- index on `(session_id, created_at)`

For this iteration, keep content blocks intentionally narrow:

- `text`
- `status` if needed for calm assistant progress/state messaging

Avoid introducing action-card, email-draft, or chart complexity until the release actually needs them.

---

## 11. Operational and Security Requirements

- continue using server-managed sessions only
- scope all chat session and message access to the authenticated user
- treat calendar event titles, descriptions, and attendee names as untrusted user data
- keep the assistant read-only for this release
- never allow prompts or calendar content to bypass server-side authorization checks
- log assistant turn lifecycle steps and failures with correlation context where available
- preserve user-safe typed errors for chat failures and unsupported requests

---

## 12. Testing Strategy

### Backend tests

- chat session list and message-history endpoints require auth
- users cannot access another user’s sessions or messages
- posting a message persists both user and assistant turns
- read-only assistant service answers from synced calendar data rather than unsourced free text
- unsupported or out-of-scope prompts return safe, clear assistant fallback behavior
- chat failure paths surface typed, user-safe errors

### Frontend tests

- chat workspace renders loading, empty, success, and error states
- sending a message shows pending state and then renders the assistant reply
- persisted session history reloads correctly
- switching sessions loads the correct message thread
- calendar workspace and chat workspace coexist without breaking core navigation

### E2E tests

- authenticated user opens the main workspace, asks a supported question, and receives an answer
- refreshing the page preserves session history
- unauthorized session access is blocked
- unsupported prompts fail gracefully without breaking the chat UI

---

## 13. Release Risks and Mitigations

### Risk: assistant responses become generic or hallucinatory

Mitigation:

- ground responses in narrow read-only calendar retrieval tools
- bound supported question types tightly for this iteration

### Risk: chat orchestration becomes tightly coupled to calendar models

Mitigation:

- query synced calendar data through a dedicated service/tool boundary
- keep chat routers and chat persistence separate from calendar ORM details

### Risk: chat layout overwhelms the calendar workspace

Mitigation:

- keep the chat surface visually restrained and editorial
- make calendar visibility remain first-class in the combined workspace

### Risk: response times feel slow or brittle

Mitigation:

- keep the first supported question set intentionally small
- return calm pending and failure states instead of blocking the whole page

---

## 14. Why This Is Better Than A Chat Shell Alone

A chat-shell milestone would prove UI plumbing, but it would not deliver trustworthy assistant value.

This slice is better because it validates:

- persisted conversation state
- the first backend assistant orchestration path
- safe read-only use of synced calendar data
- chat and calendar workspace composition
- the product’s next core promise after visibility: asking useful questions

That makes it a real release unit rather than a cosmetic messaging surface.

---

## 15. Recommended Build Order for Iteration 3

1. add `ChatSession` and `Message` persistence models with constraints
2. implement read-only chat session and message APIs
3. build the assistant orchestration service using narrow calendar retrieval/query helpers and the boundaries described in [§7 Agent Design](product-spec.md#7-agent-design)
4. support a minimal set of grounded calendar Q&A behaviors
5. build the chat workspace shell and message rendering with fixture data first
6. connect the frontend to typed chat API clients
7. integrate calendar + chat into one workspace layout
8. add loading, unsupported, empty, and failure states
9. run release smoke tests with a real connected account and real synced events

---

## 16. Exit Criteria to Start Iteration 4

After this release is stable, the next smallest valuable slice should be:

**execution preferences + blocked-time management + approval-gated action proposals for scheduling**

That would let users move from asking read-only questions to reviewing safe, assistant-generated scheduling proposals without yet opening the door to broad automatic mutations.
