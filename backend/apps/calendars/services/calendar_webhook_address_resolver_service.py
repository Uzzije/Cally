from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

from django.conf import settings

logger = logging.getLogger(__name__)


class CalendarWebhookAddressResolverService:
    webhook_path = "/api/v1/calendar/webhook/google"

    def resolve(self) -> str | None:
        """Resolve a public, allowed webhook callback URL for Google watch registrations."""
        explicit_address = (getattr(settings, "GOOGLE_CALENDAR_WEBHOOK_ADDRESS", "") or "").strip()
        backend_public_base_url = (getattr(settings, "BACKEND_PUBLIC_BASE_URL", "") or "").strip()
        serve_origin = (getattr(settings, "INNGEST_SERVE_ORIGIN", "") or "").strip()

        candidate = explicit_address
        if not candidate:
            base_url = backend_public_base_url or serve_origin
            if base_url:
                candidate = urljoin(f"{base_url.rstrip('/')}/", self.webhook_path.lstrip("/"))

        if not candidate:
            return None

        if not self._is_allowed(candidate):
            logger.warning(
                "calendar.watch.skipped",
                extra={
                    "reason": "webhook_address_invalid",
                    "webhook_address": candidate,
                },
            )
            return None

        return candidate

    def _is_allowed(self, candidate: str) -> bool:
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False

        if not settings.DEBUG:
            if parsed.scheme != "https":
                return False
            if parsed.hostname in {"localhost", "127.0.0.1"}:
                return False

        return True
