# Iteration 02 Task Breakdown

**Project:** Cal Assistant
**Iteration:** 02
**Source:** [iteration-02-release-unit.md](/Users/uzomaemuchay/DEVELOPMENT/tenex_co_cal_app/docs/iteration-02-release-unit.md)
**Design reference:** [design-theme.md](/Users/uzomaemuchay/DEVELOPMENT/tenex_co_cal_app/docs/design-theme.md)
**Delivery mode:** TDD-first

## 1. Goal

Deliver the full scope of Iteration 02:

**primary Google Calendar sync + persisted event store + read-only weekly calendar view**

This breakdown keeps the implementation aligned with:

- thin vertical slicing
- SRP and separation of concerns
- framework best practices for Django, Django Ninja, and React
- Chronicle Modern visual direction

---

## 2. Release-Level Acceptance Criteria

The release is accepted only when all of the following are true:

1. An authenticated user can trigger or receive an initial sync for their primary Google Calendar.
2. The backend persists a primary `Calendar` record and normalized `Event` records without duplication.
3. The weekly calendar UI reads event data from backend APIs backed by Postgres, not directly from Google.
4. The user can navigate backward and forward by week and see the correct range of events.
5. The UI clearly communicates `loading`, `syncing`, `ready`, `empty`, `stale`, and `failed` states.
6. A user can inspect a read-only event detail surface showing the key metadata for an event.
7. Calendar and event queries are scoped to the authenticated user's own records.
8. Timezone handling works correctly for timed events and all-day events in the weekly experience.
9. Backend and frontend tests cover the core happy path plus key edge cases before implementation is considered done.
10. Linting, type checks, and `python manage.py check` pass after implementation.

---

## 3. TDD Delivery Rules

Each task below should follow this loop:

1. Write or update the failing test first.
2. Implement the smallest code change needed to make the test pass.
3. Refactor only after behavior is protected by tests.
4. Keep routers, services, models, and UI components narrowly focused.

Practical expectations:

- backend domain logic gets unit or integration coverage before wiring routes
- frontend rendering and calendar utilities get component or unit coverage before UI polish
- E2E coverage is added after the core backend and frontend paths are already stable
- do not skip tests for “simple glue code” if that glue defines user-visible behavior or domain boundaries

---

## 4. Design Requirements From Chronicle Modern

Iteration 02 must respect the design theme in [design-theme.md](/Users/uzomaemuchay/DEVELOPMENT/tenex_co_cal_app/docs/design-theme.md).

### Required UI characteristics

- use a warm cream canvas and paper-like surfaces rather than cold SaaS panels
- keep the layout editorial and information-dense rather than overly spacious
- use terracotta as the single active accent for current day markers, primary actions, and important status cues
- use serif headlines sparingly for page identity and humanist sans for functional UI
- use mono or technical type styling for time labels and chronometric details where helpful
- keep grid lines quiet so event cards remain the visual focus
- use subtle shadows, restrained rounding, and gentle hover transitions only

### Calendar-page acceptance notes

- the weekly page should feel like a professional planner, not a generic admin dashboard
- status messaging should be calm and operational, not flashy
- loading and empty states should preserve the editorial tone of the product
- event cards should prioritize scannability: title first, then time/context

---

## 5. Task Breakdown

## 5.1 Task 1: Calendar domain persistence foundation

### Scope

- add `Calendar` model
- add `Event` model
- add constraints and indexes needed for sync and range queries
- keep one model per file if the backend structure already supports that convention

### TDD tasks

- write model tests for uniqueness and relationship rules
- write tests for time-range query support expectations where model indexes/constraints matter
- implement models and migrations
- refactor naming or field selection only after tests pass

### Acceptance criteria

1. A user can own one or more calendar records, with uniqueness enforced on `(user_id, google_calendar_id)`.
2. A calendar can own many event records, with uniqueness enforced on `(calendar_id, google_event_id)`.
3. Event records persist the minimum required read-only fields for weekly rendering and detail inspection.
4. Migrations apply cleanly.

---

## 5.2 Task 2: Google Calendar client wrapper and normalization

### Scope

- create a dedicated Google Calendar integration wrapper
- normalize Google event payloads into internal DTOs for sync
- handle timed and all-day events explicitly

### TDD tasks

- write unit tests for normalization of timed events
- write unit tests for normalization of all-day events
- write unit tests for missing optional fields such as location or description
- implement wrapper and normalization utilities
- refactor duplicated mapping logic after tests pass

### Acceptance criteria

1. Google event payloads are transformed into a consistent internal format before persistence.
2. Timed events preserve start, end, and timezone correctly.
3. All-day events are normalized safely for weekly display.
4. Optional Google fields do not break the sync path when absent.

---

## 5.3 Task 3: Initial sync service for primary calendar

### Scope

- build a calendar sync service inside the `calendars` domain
- fetch the authenticated user's primary Google Calendar
- upsert calendar and event records transactionally
- persist `sync_token` and `last_synced_at`

### TDD tasks

- write a failing service test for first-time sync creating a calendar and events
- write a failing service test for repeat sync updating existing records without duplication
- write a failing service test for sync-token persistence
- write a failing service test for sync failure surfacing a typed application error
- implement sync service
- refactor only after all sync cases are green

### Acceptance criteria

1. First-time sync creates a primary calendar record and the expected event records.
2. Repeat sync does not create duplicate calendars or duplicate events.
3. `last_synced_at` is updated after successful sync.
4. `sync_token` is persisted when returned by Google.
5. Failures are surfaced as safe application errors and logged for diagnosis.

---

## 5.4 Task 4: Calendar read API contract

### Scope

- implement `GET /api/v1/calendar/events?start=<iso>&end=<iso>`
- implement `GET /api/v1/calendar/sync-status`
- optionally implement `POST /api/v1/calendar/sync` if needed for orchestration simplicity
- keep router logic thin

### TDD tasks

- write route tests proving auth is required
- write route tests proving users can only query their own calendar data
- write route tests for correct range filtering
- write route tests for sync-status payload shape
- implement schemas, services, and routes
- refactor route/service boundaries after tests pass

### Acceptance criteria

1. Unauthenticated requests are rejected.
2. Authenticated requests return only the current user's calendar data.
3. Week-range queries return events only within the requested range.
4. Sync-status responses expose a clean frontend-facing freshness contract.
5. The API returns typed, user-safe errors for failure states.

---

## 5.5 Task 5: Frontend calendar API client and state wiring

### Scope

- add typed frontend calendar API client
- add query hooks for weekly events and sync status
- centralize error mapping and auth-aware request behavior

### TDD tasks

- write client-level tests for response mapping
- write query-hook tests for loading, success, and error state transitions
- implement the domain client and hooks
- refactor shared API concerns only after tests pass

### Acceptance criteria

1. The frontend consumes typed calendar responses through a dedicated domain client.
2. Weekly event data and sync status can be fetched independently.
3. Error states are normalized for UI consumption.
4. No page-level component performs raw `fetch` calls directly for calendar data.

---

## 5.6 Task 6: Weekly calendar page shell

### Scope

- build `CalendarPage`
- add toolbar with week navigation
- add weekly grid shell and day columns
- make the protected calendar page the authenticated default home for this release

### TDD tasks

- write component tests for initial page states
- write tests for previous/next week navigation behavior
- write tests proving the correct date range is requested when the visible week changes
- implement the page shell and state wiring
- refactor container/presentational boundaries after tests pass

### Acceptance criteria

1. Authenticated users land on the calendar page as the primary protected experience.
2. The page shows a 7-day weekly layout with clear day boundaries.
3. The user can navigate between weeks.
4. Navigation updates the requested event range correctly.

### Design-theme acceptance criteria

1. The page uses Chronicle Modern colors, restrained shadows, and editorial density.
2. The layout feels like a calendar workspace, not a generic dashboard card grid.
3. Current-day emphasis uses the terracotta accent sparingly and clearly.

---

## 5.7 Task 7: Event block rendering and layout utilities

### Scope

- render event blocks in the correct day and time position
- isolate date math and event layout logic in utilities
- support overlapping-event layout well enough for a clean read-only experience

### TDD tasks

- write unit tests for layout calculations
- write component tests for event rendering in the correct day column
- write tests for overlapping events
- write tests for all-day event presentation rules chosen for this iteration
- implement layout utilities and event block components
- refactor once layout behavior is protected

### Acceptance criteria

1. Timed events render in the expected position for the visible week.
2. Overlapping events remain readable and do not fully obscure one another.
3. All-day events are rendered in a consistent, defined way for this release.
4. Event cards prioritize title and time readability.

### Design-theme acceptance criteria

1. Event cards feel tactile and paper-like, with subtle borders or shadows.
2. Grid lines remain visually quiet.
3. Time labels are compact and precise, with chronometric styling where appropriate.

---

## 5.8 Task 8: Sync status, loading, empty, stale, and error states

### Scope

- add `SyncStatusIndicator`
- render clear UX for `loading`, `syncing`, `ready`, `empty`, `stale`, and `failed`
- ensure empty and failed states do not break week navigation or the page shell

### TDD tasks

- write component tests for each visible sync state
- write tests for stale-state messaging behavior
- write tests proving empty-state rendering does not break the weekly layout
- implement state components and wiring
- refactor copy or styling once behaviors are green

### Acceptance criteria

1. Each sync or data state has a distinct, understandable visual treatment.
2. Empty calendars produce a graceful empty state, not a broken screen.
3. Failed sync states guide the user without exposing raw backend errors.
4. Stale data is visible without making the interface feel alarming.

### Design-theme acceptance criteria

1. Status UI uses calm, editorial messaging.
2. Accent color is used deliberately, not as a noisy alert system.
3. State containers match the same tactile surface language as the rest of the page.

---

## 5.9 Task 9: Read-only event details surface

### Scope

- build read-only event detail display
- expose title, time, location, description, and basic attendees when available
- keep the interaction simple and non-mutating

### TDD tasks

- write component tests for opening and closing event details
- write tests for fallback rendering when optional fields are missing
- implement the event details panel or drawer
- refactor presentation details after behavior is protected

### Acceptance criteria

1. Users can select an event and inspect its core details.
2. Optional fields render gracefully when absent.
3. The event details surface is clearly read-only in this iteration.

### Design-theme acceptance criteria

1. Event details feel like an editorial side panel or planner detail card.
2. Typography hierarchy is clear and understated.
3. Metadata presentation remains compact and scannable.

---

## 5.10 Task 10: Integration, E2E, and release hardening

### Scope

- add end-to-end coverage for the core happy path
- verify auth-to-calendar flow
- run lint, type checks, and Django system checks
- ensure logs are present where sync diagnosis matters

### TDD tasks

- write or update E2E tests for login-to-calendar happy path
- write E2E coverage for empty-calendar behavior
- write E2E coverage for a sync-failure or stale-data state if feasible with existing tooling
- implement final glue and hardening fixes
- run verification suite

### Acceptance criteria

1. The core authenticated calendar flow is covered by E2E tests.
2. Observability exists around sync initiation, success, and failure paths.
3. Relevant linting and type-check commands pass.
4. `python manage.py check` passes using the project virtual environment.
5. The release can be demonstrated end to end without relying on manual Google reads from the frontend.

---

## 6. Recommended Build Order

1. Task 1: persistence foundation
2. Task 2: Google wrapper and normalization
3. Task 3: initial sync service
4. Task 4: calendar read API contract
5. Task 5: frontend calendar client and state
6. Task 6: weekly page shell
7. Task 7: event rendering and layout
8. Task 8: sync and empty/error states
9. Task 9: read-only event details
10. Task 10: integration and hardening

This order keeps risk-first backend integration ahead of UI polish while still following a thin vertical slice.

---

## 7. Definition of Done

Iteration 02 is done when:

- all release-level acceptance criteria are satisfied
- each task above has passing tests written in a TDD-first manner
- the weekly calendar UI visibly matches the Chronicle Modern design direction
- the code remains simple, cohesive, and not over-engineered
- lint, type checks, and Django checks pass

---

## 8. Suggested Verification Commands

Use the project virtual environment:

`source ~/DEVELOPMENT/virtualenv/t-cal-env/bin/activate`

Suggested verification sequence:

1. backend unit and integration tests
2. frontend unit and component tests
3. E2E tests for the calendar happy path
4. frontend lint and type-check
5. `python manage.py check`

If we want, the next step can be turning this breakdown into implementation tickets or a checklist doc for the repo.
