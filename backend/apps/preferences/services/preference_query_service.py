from __future__ import annotations

from django.utils import timezone

from apps.core.types import AuthenticatedUser
from apps.preferences.models.temporary_blocked_time import TemporaryBlockedTime
from apps.preferences.models.user_preferences import UserPreferences


class PreferenceQueryService:
    def get_for_user(self, user: AuthenticatedUser) -> UserPreferences:
        """Return the user's preferences, bootstrapping defaults when missing or legacy values exist."""
        preferences, _ = UserPreferences.objects.get_or_create(user=user)
        if preferences.execution_mode == "auto":
            preferences.execution_mode = "confirm"
            preferences.save(update_fields=["execution_mode", "updated_at"])
        return preferences

    def get_display_timezone(self, user: AuthenticatedUser) -> str | None:
        """Return the user's preferred display timezone (or None if unset)."""
        preferences = self.get_for_user(user)
        display_timezone = preferences.display_timezone.strip()
        return display_timezone or None

    def get_active_temporary_blocked_times(self, user: AuthenticatedUser):
        """Return currently active temporary blocked times ordered chronologically."""
        return TemporaryBlockedTime.objects.filter(
            user=user, expires_at__gt=timezone.now()
        ).order_by(
            "start_time",
            "id",
        )

    def get_active_temporary_blocked_times_by_public_ids(
        self, user: AuthenticatedUser, *, public_ids: list[str]
    ):
        """Return active temporary blocked times filtered to the requested public ids."""
        if not public_ids:
            return TemporaryBlockedTime.objects.none()

        return TemporaryBlockedTime.objects.filter(
            user=user,
            expires_at__gt=timezone.now(),
            public_id__in=public_ids,
        ).order_by(
            "start_time",
            "id",
        )
