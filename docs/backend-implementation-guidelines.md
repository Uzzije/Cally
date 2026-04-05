# Backend Implementation Guidelines

**Project:** Cal Assistant
**Status:** Implementation guideline
**Derived from:** [product-spec.md](/Users/uzomaemuchay/DEVELOPMENT/tenex_co_cal_app/docs/product-spec.md)

## 1. Purpose

This document defines how we should implement the Django backend so it remains secure, observable, scalable enough for production use, and aligned with framework best practices.

The backend must do more than expose endpoints. It must safely coordinate authentication, calendar sync, analytics, agent orchestration, and side-effect execution while preserving user trust.

---

## 2. Backend Engineering Principles

### 2.1 Product-facing principles

- **User trust first**: actions that change calendars or send emails must be intentional, traceable, and policy-aware.
- **Fresh-enough data over accidental staleness**: sync strategy must be explicit and observable.
- **Safe automation**: execution mode and rate limits are part of domain behavior, not UI-only concepts.

### 2.2 Software design principles

- **Single Responsibility Principle**: models persist state, services coordinate workflows, API schemas define contracts, and integrations wrap external systems.
- **Dependency inversion**: application services should depend on internal interfaces/wrappers, not directly on third-party SDK calls everywhere.
- **Explicit boundaries**: agent orchestration, Google integration, sync, analytics, and policy enforcement should be separate modules.
- **Fail-safe defaults**: when execution state is ambiguous, default to draft/confirm behavior, not mutation.

---

## 3. Recommended Backend Architecture

## 3.1 Architectural layers

We should structure the backend around these layers:

- **API layer**: Django Ninja routers, request validation, response schemas, auth enforcement
- **application layer**: use-case services that coordinate workflows
- **domain layer**: business rules, entities, policies, and execution constraints
- **infrastructure layer**: Google clients, Agno integration, database access helpers, Inngest functions/events

This keeps controllers thin and prevents business logic from spreading across views, models, and tasks.

## 3.1.1 Singular file and model responsibility

For Django Ninja APIs and backend domain code, we should follow a strict **singular component per file** convention wherever practical.

That means:

- one model class per model file
- one schema family per schema file when they describe one domain component
- one router module per resource/component
- one service per service file when the service has a single orchestration responsibility
- one policy/check class per file when it represents a distinct rule set

Examples:

- `models/user_profile.py`
- `models/calendar.py`
- `models/event.py`
- `api/routers/calendar_router.py`
- `api/schemas/event_schema.py`
- `services/calendar_sync_service.py`

Why we want this:

- improves discoverability
- reduces merge conflicts
- keeps files small and reviewable
- enforces SRP at the file level, not just the class level

This should be treated as the default organizational rule for Ninja-facing backend code unless a very small pair of types is inseparable and combining them is clearly simpler.

## 3.2 Suggested Django app boundaries

```text
backend/
  config/
  apps/
    core/
    accounts/
    calendars/
    chat/
    preferences/
    analytics/
    core_agent/
    bff/
```

### App responsibilities

- `core`: shared platform concerns such as common abstractions, shared utilities, base classes, and observability helpers
- `core_agent`: shared agent runtime only: Agno adapters, GAME abstractions, base tool contracts, provider interfaces, policy primitives, and eval helpers
- `accounts`: user profile data, auth integration, account lifecycle
- `calendars`: calendars, events, sync orchestration, Google Calendar integration
- `chat`: concrete conversational product domain: sessions, messages, transcript services, chat-specific capability assembly, prompt/context construction, and concrete assistant turn orchestration built on `core_agent`
- `preferences`: execution mode, blocked times, rate limits
- `analytics`: read-only query layer, chart payload assembly, SQL safety
- `bff`: backend-for-frontend endpoints and frontend-facing API contracts that compose stable payloads from internal domains without taking ownership of their business logic

### App boundaries

- `core` boundary: may provide shared primitives, base types, shared errors, logging helpers, and infrastructure abstractions; it must not absorb business logic from feature apps.
- `core_agent` boundary: may provide reusable agent kernel pieces such as Agno wrappers, GAME execution types, provider abstractions, tool metadata contracts, and shared eval harnesses; it must not import product-domain apps or own feature persistence.
- `accounts` boundary: owns user profile state, Google account linkage, auth-adjacent account lifecycle behavior, and authenticated bootstrap identity data.
- `calendars` boundary: owns calendar records, synced event state, sync workflows, availability data access, and Google Calendar integration wrappers.
- `chat` boundary: owns chat sessions, messages, structured content block persistence, conversation history retrieval, and the concrete conversational agent use cases for the chat product surface.
- `preferences` boundary: owns user-configurable behavior such as execution mode, blocked times, and future rate-limit preferences.
- `analytics` boundary: owns calendar analytics queries, approved query shapes, chart payload generation, and read-only analytical interpretation.
- `bff` boundary: owns frontend-shaped response composition and route contracts that combine data from internal apps without moving ownership of the underlying domain data or orchestration logic.

### Boundary rules

- each app owns its own models, migrations, services, and API schemas for its domain
- cross-app reads should go through services or explicit query interfaces, not direct model imports by default
- no app other than `bff` should reshape multiple domains purely for frontend convenience
- `core_agent` should remain product-agnostic and depend only on `core`
- feature domains may build concrete agent use cases on top of `core_agent`, but they remain the owners of their own persistence and domain orchestration
- `chat` may coordinate `calendars`, `preferences`, and later `analytics` for conversational use cases, but it should do so through stable services/query interfaces rather than raw model coupling where possible
- `core` is allowed to be depended on broadly, but feature apps must not leak feature-specific logic back into `core`

### Allowed dependency graph

Recommended dependency direction:

```text
core
  ^
  |
core_agent
  ^
  |
accounts      calendars      preferences      analytics
      \          |                |                /
       \         |                |               /
                     chat
                      ^
                      |
                     bff
```

Rules:

- `core` can be imported by every app
- `core_agent` may depend only on `core`
- `accounts`, `calendars`, `chat`, `preferences`, `analytics`, and `bff` may depend on `core`
- feature domains may depend on `core_agent` when they are implementing concrete agent-powered behavior
- `analytics` may depend on `calendars` for read-only event data access
- `chat` may depend on `accounts`, `calendars`, `preferences`, `analytics`, and `core_agent`
- `bff` may depend on `core`, `accounts`, `calendars`, `chat`, `preferences`, `analytics`, and `core_agent`
- peer domain apps should avoid depending on each other directly unless the dependency is stable, read-oriented, and explicitly justified

Avoid:

- `accounts` importing `chat` or `calendars`
- `calendars` importing `chat`
- `core_agent` importing `accounts`, `calendars`, `chat`, `preferences`, or `analytics`
- `chat` importing `calendars` models directly for orchestration logic when a query/service boundary would be cleaner
- `analytics` mutating other domains
- `bff` becoming a second business-logic layer

---

## 4. Model Design Guidelines

## 4.1 Use models for persistence, not orchestration

Django models should:

- represent persisted state
- define constraints and indexes
- expose limited convenience methods when genuinely local to the entity

Avoid:

- embedding complex Google API calls inside model methods
- putting agent reasoning logic in models
- coupling models directly to HTTP concerns

## 4.2 Data modeling rules

- use `DateTimeField` with timezone awareness everywhere
- add database constraints for uniqueness and referential integrity
- use `JSONField` only when the shape is flexible and query needs are modest
- add explicit enums for execution mode, message role, event status, and action status
- audit index needs early for event time ranges, user/session lookups, and sync tokens

## 4.3 Recommended constraints

Examples:

- unique `(user_id, google_calendar_id)` on calendars
- unique `(calendar_id, google_event_id)` on events
- index `Event(start_time, end_time)`
- index `Message(session_id, created_at)`
- one-to-one integrity for `UserPreferences`

---

## 5. API Design Guidelines

## 5.1 API style

Use Django Ninja as the public API contract layer.

Guidelines:

- define request and response schemas explicitly
- keep routers thin and delegate to services
- use typed DTOs instead of returning ORM models directly
- version the API from the start, even if only `v1`
- keep router files singular in responsibility, aligned to one resource/component

## 5.2 Route organization

Recommended domains:

- `/api/v1/auth/...`
- `/api/v1/calendar/...`
- `/api/v1/chat/...`
- `/api/v1/settings/...`
- `/api/v1/analytics/...`

Public route ownership does not have to match domain ownership exactly. A route may remain chat-shaped for frontend clarity while being implemented in `bff` and delegated to `chat` services internally.

Streaming endpoints should live under chat-facing routes with clear ownership in the application layer that produces those events.

Suggested module shape:

```text
apps/
  calendars/
    api/
      routers/
        calendar_router.py
        event_router.py
      schemas/
        calendar_schema.py
        event_schema.py
```

Avoid large catch-all files such as:

- `api.py`
- `schemas.py`
- `models.py`

Those files become dumping grounds and usually violate SRP quickly as the product grows.

## 5.3 Error contract

All APIs should return consistent, typed errors with:

- machine-readable code
- user-safe message
- correlation/request ID where possible

This is critical for both frontend UX and support/debugging.

---

## 6. Service Layer Design

## 6.1 Service categories

We should separate services by responsibility:

- **domain services**: business rules such as approval gating, rate-limit checks, and schedule policies
- **integration services**: Google Calendar, Gmail, contact lookup, token refresh
- **application services**: use-case orchestration such as `send_chat_message`, `sync_calendar`, `approve_actions`

## 6.2 Example service boundaries

- `CalendarSyncService`
- `GoogleCredentialService`
- `EventQueryService`
- `ChatSessionService`
- `ChatAssistantTurnService`
- `AgentProvider`
- `ApprovalPolicyService`
- `AnalyticsQueryService`
- `EmailDraftService`

This keeps side effects centralized and testable.

---

## 7. Google Integration Guidelines

## 7.1 Credentials and token handling

- all OAuth token usage must be server-side only
- refresh access tokens just-in-time before external API calls
- encrypt refresh tokens at rest
- detect revoked credentials and raise a first-class re-authentication state

## 7.2 Integration wrapper pattern

Wrap `google-api-python-client` usage in internal gateway classes. Do not spread raw Google client construction across the codebase.

Recommended wrappers:

- `GoogleCalendarGateway`
- `GoogleGmailGateway`
- `GoogleContactsGateway`

Each wrapper should:

- accept a user or credential object
- expose task-specific methods
- translate third-party exceptions into internal typed errors

---

## 8. Calendar Sync Architecture

## 8.1 Sync responsibilities

Calendar sync should be a distinct workflow, not an incidental side effect buried inside chat requests.

The sync pipeline should support:

- initial sync bootstrap
- incremental sync using `syncToken`
- on-demand freshness refresh
- conflict-safe upsert behavior
- observability on sync status and failures

## 8.2 Sync flow

Recommended flow:

1. load active calendar and sync state
2. refresh Google credentials if needed
3. fetch changes from Google
4. normalize payloads into internal event DTOs
5. upsert events in a transaction
6. persist new `sync_token` and `last_synced_at`
7. emit structured logs and metrics

## 8.3 Background processing

Use **Inngest** as the standard async execution layer for scheduled sync, retries, and event-driven workflows. The contract should assume critical async work happens outside request/response for reliability.

Rules:

- API routes and services should publish events or call Inngest-trigger wrappers, not execute long-running sync directly in request handlers.
- Keep Inngest function definitions in domain-owned modules (for example under `apps/calendars/inngest/`) rather than scattering them across views.
- Use one function/workflow per file where practical, aligned with our singular component convention.
- Define idempotency boundaries (for example `user_id + sync_window` or Google sync token checkpoints) to make retries safe.
- Use Inngest retry controls and step semantics for external calls (Google APIs) and persistence checkpoints.
- Emit structured logs at function start/finish/failure with correlation IDs so async runs can be traced back to user actions.

Recommended triggers:

- `account.connected` -> bootstrap initial calendar sync
- `calendar.sync.requested` -> on-demand sync
- scheduled `calendar.sync.scheduled` -> freshness maintenance
- `agent.action.approved` -> async execution for side-effecting operations when needed

This keeps async entrypoints explicit, domain-scoped, and production-observable.

## 8.4 Inngest boundary and ownership

- `calendars` owns calendar sync events/functions and sync-state persistence contracts.
- `core_agent` may provide shared event metadata or execution abstractions for agent-capable domains, but must not own domain persistence or domain-specific workflow state.
- `chat` may publish chat-domain async events in future iterations, but it remains the owner of conversational workflow state and message persistence.
- `bff` must never run async workflows directly; it invokes application services in the owning domain that publish domain events.
- `core` may host shared helpers for event metadata, correlation IDs, and common Inngest wiring utilities.

---

## 9. Agent Architecture

## 9.1 Agno's role

Use Agno as an orchestration layer, not as the owner of application state or external credentials.

Agno should live behind the shared `core_agent` runtime, where it provides reusable agent kernel behavior such as:

- provider integration
- tool-calling infrastructure
- GAME loop execution scaffolding
- structured response generation support

The application should still own:

- execution policy
- rate limiting
- database persistence
- Google client access
- content block validation

## 9.1.1 `core_agent` vs. feature-domain ownership

`core_agent` should provide only the reusable agent framework:

- Agno wrappers/adapters
- provider interfaces
- base tool and capability contracts
- shared policy/eval primitives
- execution-state abstractions

Feature domains should own concrete agent use cases.

For example, `chat` should own:

- chat-specific capability policy for a release
- prompt/context construction using chat history plus domain data
- registration/adaptation of read-only calendar tools
- clarification/fallback behavior for the chat UX
- assistant turn orchestration for the chat product surface

This keeps `core_agent` reusable and product-agnostic while allowing feature domains to evolve their own assistant behaviors without forcing all orchestration into one cross-domain module.

## 9.2 Tool design rules

Tools should be:

- small and single-purpose
- explicit about side effects
- idempotent where feasible
- easy to test independently from the LLM

Each tool should declare:

- input schema
- side-effect classification
- authorization requirements
- audit/logging behavior

## 9.3 Execution policy

Before any side-effecting tool runs, the backend must check:

- user execution mode
- risk level of the requested action
- rate limits
- recipient or attendee safety rules
- whether explicit approval is required

This policy must exist outside the prompt so it remains enforceable even if model behavior drifts.

---

## 10. Streaming Architecture

SSE should stream structured events, not raw string concatenation.

Recommended event types:

- `message_started`
- `content_block_delta`
- `status`
- `tool_started`
- `tool_completed`
- `approval_required`
- `message_completed`
- `error`

Benefits:

- cleaner frontend rendering
- resumable parsing
- better observability
- easier future migration to other transports if needed

---

## 11. Analytics and Text-to-SQL Safety

## 11.1 Read-only analytics boundary

Analytics must execute through a tightly controlled query layer.

Rules:

- read-only database access only
- always scoped to the authenticated user
- parameterized queries only
- allowlist query shapes or use a generated intermediate representation before SQL

## 11.2 Recommended pattern

Prefer:

1. natural language request
2. agent produces structured analytics intent
3. backend maps intent to approved query builder patterns
4. query executes through a read-only service
5. backend returns text summary plus chart payload

This is safer than letting free-form SQL flow directly from the model into the database.

---

## 12. Security, Privacy, and Safety Controls

- treat calendar event data as untrusted input for prompting
- sanitize content before placing it into model context
- log sensitive operations without leaking message bodies or tokens
- require explicit approval for bulk or risky actions
- enforce rate limits server-side regardless of frontend behavior
- protect all user data by account-level scoping at the query layer

Security controls must be coded as deterministic policy checks, not documented intentions.

---

## 13. Observability and Operations

## 13.1 Logging

Use structured logs with fields such as:

- `user_id`
- `session_id`
- `message_id`
- `calendar_id`
- `request_id`
- `tool_name`
- `sync_job_id`

## 13.2 Metrics

Track:

- sync success/failure counts
- sync duration
- tool execution counts and latency
- approval-required rate
- email send rate
- event creation rate
- SSE disconnect/error rates

## 13.3 Auditability

Side-effect actions should create an auditable record of:

- who initiated the action
- what tool executed
- whether approval was required
- whether execution succeeded or failed

---

## 14. Testing Strategy

Follow TDD for meaningful backend workflows.

### Unit tests

- policy checks
- tool input validation
- event normalization
- token refresh handling
- analytics intent mapping

### Integration tests

- OAuth/account linkage flows at the application boundary
- calendar sync persistence behavior
- chat message persistence and block serialization
- SSE event sequencing
- approval-to-execution transition

### End-to-end/system tests

- login -> sync -> ask question -> receive structured response
- propose event -> approve -> create event -> persisted confirmation
- email draft -> send flow with safety gating

Avoid tests that lock us to framework internals. Focus on business-critical behavior and failure modes.

---

## 15. Definition of Done for Backend Features

A backend feature is only done when:

- API schema is explicit and documented
- business logic lives in services, not routers
- security and policy checks are enforced server-side
- logs and metrics cover the critical path
- data model constraints are in place
- core workflows are tested
- failure handling is explicit and user-safe

---

## 16. Initial Backend Build Order

Recommended sequence:

1. Django project foundation, settings split, environment management
2. Auth and allauth headless Google login
3. Core domain models and migrations
4. Google credential service and calendar sync pipeline
5. Calendar read APIs
6. Chat session/message persistence
7. Agent orchestration and read-only tools
8. Approval-gated side-effect tools
9. Analytics query layer
10. Hardening: rate limits, audit logs, retries, observability

This order builds the highest-risk platform concerns first and reduces rework later.
