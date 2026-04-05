# Frontend Implementation Guidelines

**Project:** Cal Assistant
**Status:** Implementation guideline
**Derived from:** [product-spec.md](/Users/uzomaemuchay/DEVELOPMENT/tenex_co_cal_app/docs/product-spec.md), [design-brief.md](/Users/uzomaemuchay/DEVELOPMENT/tenex_co_cal_app/docs/design-brief.md)

## 1. Purpose

This document defines how we should implement the React frontend so it is maintainable, testable, accessible, and production-ready. It translates the product specification into engineering rules, architectural boundaries, and delivery standards.

The goal is not just to ship UI quickly. The goal is to build a frontend that:

- supports rich AI-driven interactions without becoming fragile
- keeps state predictable as calendar, chat, and settings complexity grows
- follows React and Tailwind best practices
- preserves the product's visual identity from the design brief

---

## 2. Frontend Engineering Principles

### 2.1 Product-facing principles

- **Clarity over cleverness**: calendar and chat workflows must feel obvious on first use.
- **Progressive disclosure**: show the next best action, not every possible action at once.
- **Trust-building UI**: any side effect must be understandable, reviewable, and reversible where possible.
- **Responsive by design**: mobile behavior is a first-class concern, not a later patch.

### 2.2 Software design principles

- **Single Responsibility Principle**: components should either orchestrate data, render presentation, or handle interaction logic, not all three.
- **Separation of concerns**: API clients, domain mapping, view rendering, and state transitions must live in separate modules.
- **High cohesion / low coupling**: organize by feature domain, not by technical layer alone.
- **Composition over inheritance**: React component composition should be the default extension model.
- **Explicit state transitions**: chat execution states and approval workflows should be modeled deliberately, not inferred from ad hoc booleans.

---

## 3. Recommended Frontend Architecture

## 3.1 App shape

We should implement the frontend as a feature-oriented SPA with clear boundaries:

- `app shell`: routing, layout, navigation, auth/session bootstrap
- `calendar domain`: views, event rendering, date navigation, sync freshness
- `chat domain`: sessions, message stream, block rendering, action handling
- `settings domain`: preferences, rate limits, connected account settings
- `shared UI`: reusable primitives and design-system wrappers

## 3.2 Suggested folder structure

```text
frontend/src/
  app/
    router/
    providers/
    layout/
  features/
    auth/
    onboarding/
    calendar/
      api/
      components/
      hooks/
      types/
      utils/
    chat/
      api/
      components/
      hooks/
      state/
      types/
      utils/
    settings/
      api/
      components/
      hooks/
      types/
  shared/
    api/
    components/
    hooks/
    lib/
    types/
    utils/
  styles/
```

### Why this structure

- keeps business concepts discoverable
- reduces cross-feature coupling
- supports parallel development
- makes future extraction of shared libraries easier

---

## 4. Rendering Strategy

## 4.1 Page-level composition

Primary screens should map directly to route-level containers:

- `LoginPage`
- `OnboardingPage`
- `CalendarChatPage`
- `SettingsPage`

Each page container should:

- fetch route-level data
- compose feature modules
- avoid embedding detailed business logic

## 4.2 Container vs presentational split

Use a light container/presentational model:

- **containers** own data fetching, mutations, and state orchestration
- **presentational components** receive typed props and remain stateless where practical

Example:

- `ChatPanelContainer` handles session state, streaming, and optimistic updates
- `ChatMessageList`, `ChatComposer`, and block renderers focus on UI only

This keeps components testable and reduces accidental state duplication.

---

## 5. State Management Guidelines

## 5.1 State ownership rules

- **Server state**: use a dedicated async data layer for API fetches, caching, invalidation, and mutation status
- **UI state**: local component state for ephemeral concerns such as drawer open/close, selected event, or input draft
- **Workflow state**: feature-level state for chat execution and approval flows

## 5.2 Recommendation

Use:

- **React Query / TanStack Query** for server state
- **React Hook Form + Zod** for form state and validation
- **feature-scoped reducer/state machine** for chat execution flow if complexity grows

Avoid:

- duplicating API data into global client stores without need
- deep prop drilling when composition or context would suffice
- untyped `any` payloads for agent blocks

## 5.3 Chat state model

The chat experience is stateful enough that we should model it explicitly:

- `idle`
- `submitting`
- `streaming`
- `awaiting_clarification`
- `awaiting_approval`
- `executing`
- `error`

This mirrors the product spec and prevents hidden UI inconsistencies.

---

## 6. API Integration Rules

## 6.1 API client design

All HTTP and SSE interaction should go through typed domain clients.

Example boundaries:

- `features/calendar/api/calendarClient.ts`
- `features/chat/api/chatClient.ts`
- `features/settings/api/settingsClient.ts`

Each client should:

- expose domain-level functions, not raw `fetch` calls everywhere
- map backend payloads into frontend-friendly types
- centralize error parsing and auth handling

## 6.2 Streaming

SSE streaming must be implemented behind a small abstraction so UI components do not handle transport details directly.

Recommended flow:

1. container submits message
2. client opens SSE stream
3. stream events are parsed into typed updates
4. reducer/store merges updates into the active message
5. UI renders partial text, status blocks, charts, and action cards incrementally

## 6.3 Runtime validation

Because agent block payloads are dynamic, validate response shapes at runtime using a schema layer before rendering. This protects the UI from malformed agent output and makes error handling predictable.

---

## 7. Component Architecture

## 7.1 Shared UI layer

Wrap DaisyUI primitives in local components so product styling and semantics stay under our control.

Examples:

- `Button`
- `Input`
- `Select`
- `Modal`
- `Drawer`
- `Badge`
- `Card`

This prevents framework leakage and gives us one place to enforce accessibility, variants, and design tokens.

## 7.2 Calendar components

Recommended decomposition:

- `CalendarToolbar`
- `CalendarGrid`
- `CalendarDayColumn`
- `CalendarEventBlock`
- `BlockedTimeOverlay`
- `SyncStatusIndicator`
- `EventDetailsPanel`

Rules:

- keep date math in utilities, not components
- render blocked time separately from events
- normalize event layout logic into a reusable positioning function

## 7.3 Chat components

Recommended decomposition:

- `ChatPanel`
- `ChatSessionSwitcher`
- `MessageList`
- `MessageBlockRenderer`
- `TextBlock`
- `ChartBlock`
- `ActionCardBlock`
- `EmailDraftBlock`
- `ClarificationBlock`
- `StatusBlock`
- `ChatComposer`

Rules:

- render blocks by discriminated union type
- never switch on untyped strings in multiple places
- isolate block actions so approve/send/edit handlers stay testable

---

## 8. Design System Implementation

## 8.1 Token strategy

We should define CSS variables for:

- colors
- spacing
- radius
- shadows
- typography
- chart palette

The visual system must reflect the design brief:

- warm neutrals as the base
- one restrained accent color
- serif headline typography
- subtle borders over flashy visual effects

## 8.2 Tailwind usage

Best practices:

- keep Tailwind utilities in JSX for simple composition
- extract repeated patterns into shared components, not giant utility strings
- prefer semantic component props over repeating long class sequences
- extend Tailwind theme with project tokens rather than hard-coding arbitrary values everywhere

Avoid:

- inconsistent spacing scales
- direct arbitrary colors scattered across features
- overriding DaisyUI styles ad hoc in many files

---

## 9. Accessibility and UX Quality Bar

- all interactive elements must have keyboard support
- focus order must remain logical across chat, calendar, and drawers
- color alone must not convey blocked time or event meaning
- charts require text summaries or accessible labels
- loading and streaming states must be announced clearly but quietly
- destructive actions require confirmation and clear copy

For a productivity tool, accessibility is part of trust and usability, not a compliance afterthought.

---

## 10. Error Handling and Resilience

- show actionable empty states, not generic blanks
- distinguish retryable errors from permission/session failures
- preserve unsent chat input when network requests fail
- degrade gracefully if a chart block fails to render
- surface sync freshness explicitly when calendar data may be stale

Frontend errors should be observable with structured logs and boundary-level fallbacks.

---

## 11. Testing Strategy

We should take a pragmatic TDD-oriented approach for meaningful flows.

### Test priorities

- chat block rendering by message type
- SSE streaming state transitions
- action approval and rejection flows
- settings form validation
- calendar event placement and blocked time rendering
- responsive navigation behavior for key breakpoints

### Test types

- **unit tests**: utilities, reducers, schema parsing, event layout logic
- **component tests**: block renderers, settings forms, approval cards
- **integration tests**: submit chat message -> stream response -> render blocks
- **E2E tests**: login redirect stubs, onboarding, calendar/chat happy path

Avoid over-testing:

- DaisyUI internals
- Tailwind class names as implementation details
- trivial passthrough components

---

## 12. Observability and Debuggability

- add structured client logs around chat lifecycle and approval actions
- tag logs with `sessionId`, `messageId`, and `requestId` when available
- capture stream open/close/error events
- expose non-sensitive sync freshness and request state in the UI

We should optimize for fast diagnosis of production issues without exposing private user data.

---

## 13. Security and Safety Expectations

- never trust event content or agent-generated block payloads without validation
- sanitize markdown and user-generated text before rendering
- do not store OAuth tokens or sensitive auth artifacts in browser storage
- use HTTP-only session cookies wherever possible
- confirm destructive or external side-effect actions in the UI

The frontend must reinforce backend safeguards, not bypass them.

---

## 14. Definition of Done for Frontend Features

A frontend feature is only done when:

- domain boundaries are clear
- types and runtime validation are in place
- loading, empty, error, and success states are handled
- accessibility considerations are covered
- core behavior is tested
- telemetry/logging exists for critical workflows
- the UI aligns with the design brief and product spec

---

## 15. Initial Frontend Build Order

Recommended delivery sequence:

1. App shell, routing, auth/session bootstrap
2. Design tokens and shared UI wrappers
3. Main calendar weekly view with static data
4. Chat panel with typed block renderer
5. SSE streaming integration
6. Settings and onboarding flows
7. Responsive behaviors and mobile navigation
8. Hardening, accessibility, and E2E coverage

This sequence reduces integration risk and establishes stable foundations before richer agent behaviors land.
