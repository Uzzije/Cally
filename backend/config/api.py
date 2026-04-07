from ninja import NinjaAPI

from apps.analytics.api.routers.saved_insight_router import router as saved_insight_router
from apps.accounts.api.routers.auth_router import router as auth_router
from apps.bff.api.routers.chat_router import router as chat_router
from apps.calendars.api.routers.calendar_router import router as calendar_router
from apps.preferences.api.routers.preferences_router import router as preferences_router

api = NinjaAPI(
    title="Cal Assistant API",
    version="1.0.0",
    urls_namespace="api",
)

api.add_router("/auth/", auth_router)
api.add_router("/calendar/", calendar_router)
api.add_router("/settings/", preferences_router)
api.add_router("/", saved_insight_router)
api.add_router("/", chat_router)
