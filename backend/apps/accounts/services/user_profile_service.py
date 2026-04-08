from typing import Any

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model

from apps.accounts.models.user_profile import UserProfile

User = get_user_model()


def ensure_user_profile(user: Any, social_account: SocialAccount | None = None) -> UserProfile:
    """Create/update the user's profile, optionally syncing fields from their Google social account."""
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if social_account is None:
        social_account = SocialAccount.objects.filter(user=user, provider="google").first()

    if social_account is not None:
        profile.google_account_id = social_account.uid or profile.google_account_id
        extra_data = social_account.extra_data or {}
        avatar_url = extra_data.get("picture", "")
        if avatar_url:
            profile.avatar_url = avatar_url
        profile.save()

    return profile
