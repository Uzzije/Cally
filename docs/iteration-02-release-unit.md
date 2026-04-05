# Iteration 02 Release Unit

**Project:** Cal Assistant
**Release theme:** Synced calendar visibility
**Status:** Proposed second releasable slice

## 1. Recommendation

The next release unit should be:

**primary Google Calendar sync + persisted event store + read-only weekly calendar view**

This is the right second slice because it builds directly on the authenticated foundation from Iteration 01 and delivers the first clear product value: the user can actually see their calendar inside the app.

This follows sound iterative delivery principles:

- **thin vertical slices**
- **highest-value next capability**
- **separation of concerns**
- **single responsibility across sync, query, and rendering layers**

It is also the smallest slice that proves the critical architecture decision from the product spec: **Google calendar data is synced into Postgres and rendered from our local store, not read live from Google on every page load.**

---

## 2. Iteration Goal

Ship the smallest production-credible version of Cal Assistant where an authenticated user can:

1. connect through the existing Google-authenticated flow
2. trigger or receive an initial primary calendar sync
3. have calendar and event data persisted locally
4. open a protected calendar page
5. view their week in a read-only calendar layout
6. inspect basic event details
7. understand whether calendar data is fresh, loading, empty, or failed

This is enough to release as an internal alpha that demonstrates the first real product utility, not just infrastructure readiness.

---

## 3. What Is In Scope

### Frontend

- protected calendar page as the authenticated default home
- weekly calendar grid for a 7-day time-based view
- previous/next week navigation
- event block rendering from API data
- sync freshness indicator
- empty, loading, stale, and error states
- event details surface for read-only inspection

### Backend

- primary calendar domain bootstrap
- calendar and event persistence models
- Google Calendar integration wrapper
- initial sync workflow for primary calendar
- incremental sync support shape using `syncToken`
- calendar range query endpoint for weekly view
- sync status exposure for frontend freshness display

### Data

- primary calendar record per user
- synced event records
- `last_synced_at`
- `sync_token`
- normalized event details needed for read-only rendering

---

## 4. What Is Out of Scope

- event create, update, or delete actions
- multi-calendar selection or management
- month view
- blocked time overlays from user preferences
- Gmail actions
- chat message flows
- analytics and charts
- background sync scheduling sophistication beyond what is required to prove the contract

Keeping these out preserves a clean slice and avoids mixing read-only calendar delivery with agent and mutation complexity too early.

---

## 5. User Story for Release 2

**As an authenticated user, I want to see my primary Google Calendar in a weekly view inside the app, so I can trust that my calendar is connected, synced, and ready for future assistant workflows.**

---

## 6. User Experience Flow

```text
User signs in
  -> App loads protected home
  -> Calendar bootstrap checks sync state
  -> Initial sync runs if needed
  -> Events are persisted locally
  -> Weekly calendar view requests current week range
  -> Backend returns synced events from Postgres
  -> User sees weekly calendar grid
  -> User can move week-to-week and inspect event details
  -> User sees freshness or retry state if sync is stale or failed
```

---

## 7. Success Criteria

This iteration is done when:

- a signed-in user can complete an initial sync for their primary Google Calendar
- synced calendars and events are persisted correctly in Postgres
- the frontend weekly view renders event data from backend APIs, not directly from Google
- users can navigate between weeks and fetch the correct event range
- sync freshness is visible in the UI
- empty-calendar and sync-failure states are handled clearly
- core sync and read flows are covered by tests

---

## 8. Proposed Architecture Slice

## 8.1 Frontend components

```text
AppShell
  -> CalendarPage
       -> CalendarToolbar
       -> SyncStatusIndicator
       -> CalendarWeekView
            -> CalendarDayColumn
            -> CalendarEventBlock
       -> EventDetailsPanel
```

### Frontend responsibilities

- request week-range calendar data from typed API clients
- render a stable weekly layout from normalized event payloads
- separate page orchestration from presentational calendar components
- expose freshness, loading, empty, and error states clearly
- keep date math and event layout logic out of UI components

## 8.2 Backend components

```text
calendars app
  -> calendar model
  -> event model
  -> Google Calendar client wrapper
  -> calendar sync service
  -> calendar range query service
  -> calendar API router
```

### Backend responsibilities

- fetch primary calendar data from Google using server-side credentials
- normalize Google payloads into internal DTOs
- upsert calendars and events transactionally
- persist `sync_token` and `last_synced_at`
- expose frontend-shaped read models through thin API routes

This keeps responsibilities aligned with SRP and avoids leaking Google SDK concerns into routers or frontend contracts.

---

## 9. Suggested Backend Contract

### `GET /api/v1/calendar/events?start=<iso>&end=<iso>`

Purpose:

- return synced events for the authenticated user within a requested time range

Example response:

```json
{
  "calendar": {
    "id": "uuid",
    "name": "Primary",
    "is_primary": true,
    "last_synced_at": "2026-04-04T14:30:00Z"
  },
  "events": [
    {
      "id": "uuid",
      "google_event_id": "abc123",
      "title": "Design Review",
      "start_time": "2026-04-06T14:00:00Z",
      "end_time": "2026-04-06T15:00:00Z",
      "timezone": "America/New_York",
      "location": "Zoom",
      "status": "confirmed"
    }
  ]
}
```

### `GET /api/v1/calendar/sync-status`

Purpose:

- return primary-calendar sync state for the authenticated user

Example response:

```json
{
  "has_calendar": true,
  "sync_state": "ready",
  "last_synced_at": "2026-04-04T14:30:00Z",
  "is_stale": false
}
```

### Optional sync trigger

If implementation simplicity requires it, we may expose:

`POST /api/v1/calendar/sync`

Purpose:

- trigger an initial or on-demand sync for the authenticated user's primary calendar

If we add this endpoint, it should remain narrowly scoped to sync orchestration and not become a catch-all calendar action endpoint.

---

## 10. Suggested Data Model Additions

### `Calendar`

- `id`
- `user_id`
- `google_calendar_id`
- `name`
- `is_primary`
- `color`
- `sync_token`
- `last_synced_at`
- `created_at`
- `updated_at`

Recommended constraints:

- unique `(user_id, google_calendar_id)`

### `Event`

- `id`
- `calendar_id`
- `google_event_id`
- `title`
- `description`
- `start_time`
- `end_time`
- `timezone`
- `location`
- `status`
- `attendees`
- `organizer_email`
- `created_at`
- `updated_at`

Recommended constraints:

- unique `(calendar_id, google_event_id)`
- index on event time range queries

Only store fields needed for read-only calendar rendering and event inspection in this iteration. Avoid premature support for mutation-specific metadata if it is not yet used.

---

## 11. Operational and Security Requirements

- continue using server-managed sessions only
- keep Google credentials and refresh handling server-side
- never expose OAuth tokens to frontend responses or logs
- treat sync failures as observable, typed application errors
- ensure event queries are scoped to the authenticated user's calendars only
- log sync lifecycle steps with request or correlation identifiers where available

---

## 12. Testing Strategy

### Backend tests

- initial primary calendar sync creates calendar and event records correctly
- repeat sync updates existing records without duplication
- calendar event range endpoint requires auth
- calendar event range endpoint returns only the authenticated user's events
- sync status endpoint returns expected freshness payload
- sync failure paths surface typed, user-safe errors

### Frontend tests

- weekly calendar page renders loading, empty, success, and error states
- week navigation requests the correct date ranges
- event blocks render at the expected day and time positions
- sync freshness state is displayed clearly
- event details open with expected read-only information

### E2E tests

- authenticated user lands on calendar page and sees synced events
- empty calendar account renders a graceful empty state
- failed sync or stale data path surfaces recovery guidance without breaking navigation

---

## 13. Release Risks and Mitigations

### Risk: Google event normalization is more complex than expected

Mitigation:

- support a minimal normalized field set first
- explicitly test timezone and all-day edge cases early

### Risk: sync logic becomes tangled with request/response code

Mitigation:

- keep sync orchestration in a dedicated calendar service
- keep routers thin and query-oriented

### Risk: weekly event layout bugs reduce trust quickly

Mitigation:

- isolate date math and layout logic in testable utilities
- cover overlapping events and boundary-time cases with focused tests

### Risk: freshness state is confusing to users

Mitigation:

- use explicit UI states such as syncing, ready, stale, empty, and failed
- expose `last_synced_at` consistently

---

## 14. Why This Is Better Than Sync Alone

A sync-only milestone would prove backend plumbing, but it would not deliver a user-visible outcome.

This slice is better because it validates:

- Google Calendar integration
- normalized local persistence
- calendar query boundaries
- frontend rendering architecture
- user trust through visible freshness and error handling

That makes it a real release unit rather than a hidden technical checkpoint.

---

## 15. Recommended Build Order for Iteration 2

1. add `Calendar` and `Event` persistence models with constraints
2. implement Google Calendar client wrapper and event normalization
3. build initial sync service for the primary calendar
4. expose sync status and range-query endpoints
5. build weekly calendar view with static fixtures first
6. connect the frontend to typed calendar API clients
7. add freshness, empty, loading, and error states
8. cover core sync and weekly-view behavior with tests
9. run release smoke tests against a real connected account

---

## 16. Exit Criteria to Start Iteration 3

After this release is stable, the next smallest valuable slice should be:

**read-only chat workspace + persisted chat sessions + basic natural-language calendar Q&A over synced data**

That would let users move from simply seeing their schedule to asking the assistant useful questions about it without yet introducing approval-gated mutations.
