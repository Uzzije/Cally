from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.services.user_profile_service import ensure_user_profile

User = get_user_model()


class UserProfileServiceTests(TestCase):
    def test_ensure_user_profile_creates_profile_without_social_account(self):
        user = User.objects.create_user(
            username="ignored",
            email="plain@example.com",
            password="test-pass-123",
        )

        profile = ensure_user_profile(user)

        self.assertEqual(profile.user, user)
        self.assertEqual(profile.google_account_id, "")
        self.assertEqual(profile.avatar_url, "")

    def test_ensure_user_profile_syncs_google_social_account_fields(self):
        user = User.objects.create_user(
            username="ignored",
            email="social@example.com",
            password="test-pass-123",
        )
        social_account = SocialAccount.objects.create(
            user=user,
            provider="google",
            uid="google-uid-123",
            extra_data={
                "picture": "https://example.com/social-avatar.png",
            },
        )

        profile = ensure_user_profile(user, social_account=social_account)

        self.assertEqual(profile.google_account_id, "google-uid-123")
        self.assertEqual(profile.avatar_url, "https://example.com/social-avatar.png")
