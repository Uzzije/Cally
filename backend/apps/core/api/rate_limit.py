from __future__ import annotations

import json
import logging

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


def rate_limited_response(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Custom view invoked by django-ratelimit's RatelimitMiddleware.

    Returns a 429 JSON response that matches the project's ErrorResponseSchema
    contract so the frontend can handle it consistently alongside other API errors.
    """
    user = getattr(request, "user", None)
    user_id = getattr(user, "id", None) if user else None

    logger.warning(
        "rate_limit.exceeded path=%s method=%s user_id=%s ip=%s",
        request.path,
        request.method,
        user_id,
        request.META.get("REMOTE_ADDR"),
    )

    body = json.dumps({"detail": "Rate limit exceeded. Please try again shortly."})
    response = HttpResponse(body, content_type="application/json", status=429)
    response["Retry-After"] = "60"
    return response
