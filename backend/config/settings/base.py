import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


def get_env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def get_env_bool(name: str, default: bool) -> bool:
    return get_env(name, str(default)).lower() == "true"


def build_frontend_url(base_url: str, path: str) -> str:
    normalized_base_url = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{normalized_base_url}{normalized_path}"


def get_env_choice(name: str, default: str, allowed_values: set[str]) -> str:
    value = get_env(name, default)
    if value not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise ValueError(f"{name} must be one of: {allowed}")
    return value


def is_production_like_runtime() -> bool:
    return get_env("DJANGO_ENV", "development").strip().lower() in {
        "production",
        "staging",
    }


def get_secret_key() -> str:
    secret_key = get_env("DJANGO_SECRET_KEY", None)
    if secret_key:
        return secret_key

    if is_production_like_runtime():
        raise ValueError("DJANGO_SECRET_KEY must be set when DJANGO_ENV is production-like.")

    return "django-insecure-change-me"


def get_debug_setting() -> bool:
    explicit_debug = get_env("DJANGO_DEBUG", None)
    if explicit_debug is not None:
        return explicit_debug.lower() == "true"

    return not is_production_like_runtime()


def get_google_oauth_scopes() -> list[str]:
    scopes = [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ]

    if get_env_bool("GOOGLE_OAUTH_ENABLE_GMAIL_ACTIONS", True):
        scopes.extend(
            [
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.compose",
            ]
        )

    return scopes


SECRET_KEY = get_secret_key()
DEBUG = get_debug_setting()

ALLOWED_HOSTS = [
    host.strip()
    for host in get_env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in get_env(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "http://localhost:3002,http://127.0.0.1:3002",
    ).split(",")
    if origin.strip()
]

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in get_env(
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "http://localhost:3002,http://127.0.0.1:3002",
    ).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "corsheaders",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "apps.core",
    "apps.accounts",
    "apps.core_agent",
    "apps.calendars",
    "apps.analytics",
    "apps.chat",
    "apps.preferences",
    "apps.bff",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BACKEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

USE_POSTGRES = get_env_bool("POSTGRES_ENABLED", False)

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": get_env("POSTGRES_DB", "tenex_cal"),
            "USER": get_env("POSTGRES_USER", "postgres"),
            "PASSWORD": get_env("POSTGRES_PASSWORD", "postgres"),
            "HOST": get_env("POSTGRES_HOST", "localhost"),
            "PORT": get_env("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BACKEND_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = get_env("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BACKEND_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_ONLY = True
SOCIALACCOUNT_LOGIN_ON_GET = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [
            {
                "client_id": get_env("GOOGLE_CLIENT_ID", ""),
                "secret": get_env("GOOGLE_CLIENT_SECRET", ""),
                "key": "",
            }
        ],
        "SCOPE": get_google_oauth_scopes(),
        "AUTH_PARAMS": {
            "access_type": "offline",
            "prompt": "consent",
        },
        "OAUTH_PKCE_ENABLED": True,
        "FETCH_USERINFO": True,
    }
}

FRONTEND_BASE_URL = get_env("FRONTEND_BASE_URL", "http://localhost:3002")
BACKEND_PUBLIC_BASE_URL = get_env("BACKEND_PUBLIC_BASE_URL", "")
GOOGLE_TOKEN_ENCRYPTION_KEY = get_env("GOOGLE_TOKEN_ENCRYPTION_KEY", "")
OPENAI_API_KEY = get_env("OPENAI_API_KEY", None)
AGNO_MODEL_ID = get_env("AGNO_MODEL_ID", "gpt-5-mini")

# Iteration 1 uses browser redirect OAuth (Google -> callback -> frontend).
# Keep headless URLs available, but do not force headless-only mode by default.
HEADLESS_ONLY = get_env_bool("HEADLESS_ONLY", False)
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": get_env(
        "FRONTEND_AUTH_VERIFY_EMAIL_URL",
        build_frontend_url(FRONTEND_BASE_URL, "/auth/verify-email/{key}"),
    ),
    "account_reset_password": get_env(
        "FRONTEND_AUTH_PASSWORD_RESET_URL",
        build_frontend_url(FRONTEND_BASE_URL, "/auth/password/reset"),
    ),
    "account_reset_password_from_key": get_env(
        "FRONTEND_AUTH_PASSWORD_RESET_KEY_URL",
        build_frontend_url(FRONTEND_BASE_URL, "/auth/password/reset/key/{key}"),
    ),
    "account_signup": get_env(
        "FRONTEND_AUTH_SIGNUP_URL",
        build_frontend_url(FRONTEND_BASE_URL, "/auth/signup"),
    ),
    "socialaccount_login_error": get_env(
        "FRONTEND_AUTH_ERROR_URL",
        build_frontend_url(FRONTEND_BASE_URL, "/auth/error"),
    ),
}

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = get_env_choice(
    "DJANGO_SESSION_COOKIE_SAMESITE",
    "Lax",
    {"Lax", "Strict", "None"},
)
CSRF_COOKIE_SAMESITE = get_env_choice(
    "DJANGO_CSRF_COOKIE_SAMESITE",
    "Lax",
    {"Lax", "Strict", "None"},
)

LOGIN_REDIRECT_URL = FRONTEND_BASE_URL
LOGOUT_REDIRECT_URL = FRONTEND_BASE_URL

INNGEST_APP_ID = get_env("INNGEST_APP_ID", "cal-assistant-backend")
INNGEST_BASE_URL = get_env("INNGEST_BASE_URL", "http://localhost:8288")
INNGEST_EVENT_KEY = get_env("INNGEST_EVENT_KEY", "dev-event-key")
INNGEST_SIGNING_KEY = get_env(
    "INNGEST_SIGNING_KEY",
    "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
)
INNGEST_SERVE_ORIGIN = get_env("INNGEST_SERVE_ORIGIN", None)
INNGEST_SERVE_PATH = get_env("INNGEST_SERVE_PATH", "/api/inngest")
GOOGLE_CALENDAR_WEBHOOK_ADDRESS = get_env("GOOGLE_CALENDAR_WEBHOOK_ADDRESS", "")
GOOGLE_CALENDAR_WEBHOOK_TTL_SECONDS = int(get_env("GOOGLE_CALENDAR_WEBHOOK_TTL_SECONDS", "604800"))

LOG_LEVEL = get_env("LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "apps.accounts": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "apps.chat": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "apps.bff": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
