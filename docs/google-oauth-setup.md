# Google OAuth Setup

**Purpose:** Configure Google OAuth for local/dev authentication and calendar sync.

## Required backend env vars

Set these in `backend/.env`:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

## Local redirect URI

For local backend development on port `8002` (see `docker-compose.yml`), configure this exact redirect URI in Google Cloud:

- `http://localhost:8002/accounts/google/login/callback/`

You may also add:

- `http://127.0.0.1:8002/accounts/google/login/callback/`

Important:

- Google requires an exact match on scheme + host + port + path.
- Keep the trailing slash in `/callback/`.
- If Django initiates login from `localhost:8002`, the redirect URI sent to Google is `http://localhost:8002/accounts/google/login/callback/`.
- If only `127.0.0.1` is registered (or vice versa), Google returns `Error 400: redirect_uri_mismatch`.

## Local JavaScript origins

Add these origins in Google Cloud if the frontend will run locally:

- `http://localhost:3002`
- `http://127.0.0.1:3002`

## Live deployment (Render Example)

For a two-service Render deployment, use the backend Render URL as the Google OAuth redirect URI:

- `https://<backend-service>.onrender.com/accounts/google/login/callback/`

Set these backend env vars in Render:

- `DJANGO_SETTINGS_MODULE=config.settings.prod`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS=<backend-service>.onrender.com`
- `DJANGO_CORS_ALLOWED_ORIGINS=https://<frontend-service>.onrender.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://<frontend-service>.onrender.com`
- `FRONTEND_BASE_URL=https://<frontend-service>.onrender.com`
- `BACKEND_PUBLIC_BASE_URL=https://<backend-service>.onrender.com`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_TOKEN_ENCRYPTION_KEY`
- `GOOGLE_CALENDAR_WEBHOOK_TTL_SECONDS=604800`

Optional override:

- `GOOGLE_CALENDAR_WEBHOOK_ADDRESS`

Notes:

- If `GOOGLE_CALENDAR_WEBHOOK_ADDRESS` is blank, the backend derives the webhook URL as `<BACKEND_PUBLIC_BASE_URL>/api/v1/calendar/webhook/google`.
- In production, the webhook URL must be public `https://` and cannot point at `localhost`.
- `GOOGLE_TOKEN_ENCRYPTION_KEY` should be a Fernet-compatible base64 key. If blank, the app derives an encryption key from Django `SECRET_KEY`.
- If watch registration fails or a watch expires, calendar sync still falls back safely to manual or polling-friendly refresh flows until the next successful renewal.

Cookie policy defaults to `Lax`. If browser testing on Render shows the frontend cannot send the session reliably to the backend, switch both of these to `None`:

- `DJANGO_SESSION_COOKIE_SAMESITE`
- `DJANGO_CSRF_COOKIE_SAMESITE`

When using `None`, keep production secure cookies enabled, which your `config.settings.prod` already does.

Optional frontend auth route overrides are available if your production frontend uses different auth paths:

- `FRONTEND_AUTH_VERIFY_EMAIL_URL`
- `FRONTEND_AUTH_PASSWORD_RESET_URL`
- `FRONTEND_AUTH_PASSWORD_RESET_KEY_URL`
- `FRONTEND_AUTH_SIGNUP_URL`
- `FRONTEND_AUTH_ERROR_URL`

Set this frontend env var in Render:

- `VITE_BACKEND_BASE_URL=https://<backend-service>.onrender.com`

Important:

- Google requires an exact match on scheme + host + path for the redirect URI.
- If your OAuth consent screen is still in `Testing`, add your production users as test users or Google sign-in will be blocked.
- This app currently relies on Django session cookies and `credentials: include`, so backend/frontend origins must match your configured CORS and CSRF settings.

## Google Cloud setup

1. Create or select a Google Cloud project.
2. Configure the OAuth consent screen.
3. Create an OAuth Client ID with application type `Web application`.
4. Add the authorized JavaScript origins.
5. Add the authorized redirect URI for Django allauth.
6. Copy the client ID and client secret into `backend/.env` for local work, and into Render environment variables for production.

## Backend endpoints involved

- allauth account routes: `/accounts/`
- allauth headless API routes: `/_allauth/`
- local bootstrap endpoint: `/api/v1/auth/me`

## Notes

- We request `offline` access so Google can return a refresh token for later calendar sync (and optional future Gmail send).
- We enable PKCE and `FETCH_USERINFO` so Google profile data such as avatar URL is available more reliably.
- Provider credentials are configured in settings via `SOCIALACCOUNT_PROVIDERS["google"]["APPS"]`, matching current allauth provider configuration guidance.

## References

- [django-allauth headless installation](https://docs.allauth.org/en/dev/headless/installation.html)
- [django-allauth provider configuration](https://docs.allauth.org/en/latest/socialaccount/provider_configuration.html)
- [django-allauth Google provider](https://docs.allauth.org/en/latest/socialaccount/providers/google.html)
