# Iteration 01 Release Unit

**Project:** Cal Assistant
**Release theme:** Authenticated product foundation
**Status:** Proposed first releasable slice

## 1. Recommendation

The first release unit should **not** be authentication in isolation.

Authentication alone is a technical milestone, but it is not a meaningful product slice. A better first release unit is:

**Google sign-in + authenticated app shell + session bootstrap + onboarding start + connected-account state**

This gives us a true end-to-end vertical slice that:

- proves the hardest integration boundary early
- gives us a shippable internal alpha
- establishes the foundation every later feature depends on
- lets us validate auth, routing, sessions, protected APIs, and initial user provisioning in production

This follows good iterative delivery principles:

- **thin vertical slices**
- **highest-risk integration first**
- **working software over partial layers**

---

## 2. Iteration Goal

Ship the smallest production-credible version of Cal Assistant where a user can:

1. land on a branded login page
2. sign in with Google
3. complete backend session establishment
4. enter a protected app area
5. see that their Google account is connected
6. complete or skip a lightweight onboarding step
7. sign out safely

This is enough to release as an internal or limited alpha while we continue building calendar sync and chat.

---

## 3. What Is In Scope

### Frontend

- login page
- Google sign-in CTA
- auth callback handling
- protected route/app shell
- minimal onboarding flow shell
- account status view in app
- sign-out action
- loading, error, and expired-session states

### Backend

- Django project bootstrap
- allauth headless configuration
- Google OAuth provider setup
- user provisioning on first login
- session/auth endpoints
- protected `me` endpoint
- logout endpoint
- minimal onboarding status persistence

### Data

- user record creation
- Google account linkage
- token storage through allauth
- basic profile fields
- onboarding completion flag

---

## 4. What Is Out of Scope

- calendar sync
- event ingestion
- chat session/message workflows
- SSE streaming
- analytics
- Gmail actions
- OR-Tools scheduling
- settings beyond minimal account state

Keeping these out is what makes this release small enough to build and ship cleanly.

---

## 5. User Story for Release 1

**As a new user, I want to sign in with Google and enter the product securely, so I know my account is connected and ready for future calendar features.**

---

## 6. User Experience Flow

```text
Visit app
  -> Login page
  -> Click "Sign in with Google"
  -> Complete Google OAuth
  -> Backend creates or links user
  -> Redirect into protected app shell
  -> Fetch current session/user
  -> Show onboarding step or account-ready screen
  -> User can sign out
```

---

## 7. Success Criteria

This iteration is done when:

- a new user can sign in with Google successfully
- a returning user can sign in and reach the protected app
- the app can fetch authenticated session/user data from the backend
- unauthenticated users cannot access protected routes
- logout clears the session correctly
- onboarding state is persisted and reflected
- core auth flows are covered by tests

---

## 8. Proposed Architecture Slice

## 8.1 Frontend components

```text
App
  -> PublicRoutes
       -> LoginPage
  -> ProtectedRoutes
       -> AppShell
            -> OnboardingPage (first login or incomplete)
            -> HomePlaceholderPage
                 -> AccountStatusCard
                 -> SignOutButton
```

### Frontend responsibilities

- start auth flow
- hydrate current user session
- guard protected routes
- render onboarding status
- handle auth loading and error states

## 8.2 Backend components

```text
accounts app
  -> auth configuration
  -> user profile model/extensions
  -> user provisioning service
  -> session/me API
  -> logout API
```

### Backend responsibilities

- complete OAuth handshake
- store linked social account/token data
- provision user safely
- expose authenticated user bootstrap payload
- enforce session auth on protected endpoints

---

## 9. Suggested Backend Contract

### `GET /api/v1/auth/me`

Purpose:

- return current authenticated user bootstrap payload

Example response:

```json
{
  "authenticated": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "Jane Doe",
    "avatar_url": "https://...",
    "has_google_account": true,
    "onboarding_completed": false
  }
}
```

### `POST /api/v1/auth/logout`

Purpose:

- terminate the current authenticated session

### Optional bootstrap endpoint

We may also use a single bootstrap payload endpoint later if we want auth + preferences + sync status in one request, but for this iteration `me` is enough.

---

## 10. Suggested Data Model Additions

We can keep this intentionally small.

### `User`

- `id`
- `email`
- `display_name`
- `google_account_id`
- `created_at`
- `updated_at`

### `UserPreferences` or `UserProfile`

For iteration 1, persist only what we need:

- `user_id`
- `onboarding_completed`
- `created_at`
- `updated_at`

If onboarding preferences are not yet implemented, avoid inventing premature fields.

---

## 11. Security Requirements

- use server-managed sessions, not client-managed tokens in browser storage
- store OAuth tokens only server-side
- protect all private endpoints with session auth
- handle revoked or failed OAuth flows gracefully
- do not expose token values to frontend logs or responses

---

## 12. Testing Strategy

### Backend tests

- first-time Google login provisions user correctly
- returning login links to existing user correctly
- `me` endpoint requires auth
- `me` endpoint returns expected bootstrap payload
- logout invalidates session

### Frontend tests

- login page renders correctly
- protected routes redirect when unauthenticated
- authenticated bootstrap renders app shell
- onboarding gate behaves correctly
- logout returns user to public state

### E2E tests

- sign in flow with mocked/stubbed OAuth callback
- access protected route after login
- sign out flow

---

## 13. Release Risks and Mitigations

### Risk: OAuth integration complexity

Mitigation:

- solve this first before calendar or agent work

### Risk: session/cookie misconfiguration across frontend and backend

Mitigation:

- verify local and deployed cookie settings early

### Risk: unclear onboarding state ownership

Mitigation:

- keep onboarding state minimal in this iteration

---

## 14. Why This Is Better Than Auth Alone

Auth-only gives us a backend milestone.

This slice gives us a usable release unit because it validates:

- product entry point
- user provisioning
- protected application shell
- authenticated API contract
- initial persistence pattern
- deployability

That makes it the better first release.

---

## 15. Recommended Build Order for Iteration 1

1. Django project setup and auth configuration
2. Google OAuth provider wiring with allauth
3. user provisioning flow
4. `GET /api/v1/auth/me` and logout endpoint
5. React app shell and route guard
6. login page and callback handling
7. onboarding gate and placeholder authenticated home
8. automated tests
9. deployment smoke test

---

## 16. Exit Criteria to Start Iteration 2

After this release is stable, the next smallest valuable slice should be:

**primary calendar sync + basic weekly read-only calendar view**

That would give us the first genuinely useful calendar capability on top of the authenticated foundation.
