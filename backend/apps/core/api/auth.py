from __future__ import annotations

from django.http import HttpRequest


def session_auth(request: HttpRequest):
    """Django Ninja auth callable for session-based authentication.

    Returns the authenticated user (truthy) or None (triggers 401).
    Designed for use with ``Router(auth=session_auth)`` or per-endpoint
    ``auth=session_auth``.
    """
    if request.user.is_authenticated:
        return request.user
    return None
