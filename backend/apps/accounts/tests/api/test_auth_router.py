from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models.user_profile import UserProfile

User = get_user_model()


class AuthRouterTests(TestCase):
    def test_google_login_route_is_registered(self):
        login_url = reverse("google_login")

        self.assertEqual(login_url, "/accounts/google/login/")

    def test_me_returns_unauthenticated_payload_for_anonymous_user(self):
        response = self.client.get("/api/v1/auth/me", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": False,
                "user": None,
            },
        )

    def test_me_returns_authenticated_payload_for_logged_in_user(self):
        user = User.objects.create_user(
            username="ignored",
            email="jane@example.com",
            password="test-pass-123",
            first_name="Jane",
            last_name="Doe",
        )
        profile = user.profile
        profile.google_account_id = "google-user-123"
        profile.avatar_url = "https://example.com/avatar.png"
        profile.onboarding_completed = True
        profile.save()

        self.client.force_login(user)

        response = self.client.get("/api/v1/auth/me", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "authenticated": True,
                "user": {
                    "id": user.id,
                    "email": "jane@example.com",
                    "display_name": "Jane Doe",
                    "avatar_url": "https://example.com/avatar.png",
                    "has_google_account": True,
                    "onboarding_completed": True,
                },
            },
        )

    def test_logout_clears_authenticated_session(self):
        user = User.objects.create_user(
            username="ignored",
            email="logout@example.com",
            password="test-pass-123",
        )
        self.client.force_login(user)

        response = self.client.post("/api/v1/auth/logout", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})

        me_response = self.client.get("/api/v1/auth/me", HTTP_HOST="localhost")
        self.assertEqual(
            me_response.json(),
            {
                "authenticated": False,
                "user": None,
            },
        )

    def test_complete_onboarding_updates_profile(self):
        user = User.objects.create_user(
            username="ignored",
            email="onboarding@example.com",
            password="test-pass-123",
        )
        self.client.force_login(user)

        response = self.client.post("/api/v1/auth/onboarding/complete", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})

        user.profile.refresh_from_db()
        self.assertTrue(user.profile.onboarding_completed)

    def test_creating_user_creates_profile_via_signal(self):
        user = User.objects.create_user(
            username="ignored",
            email="profile@example.com",
            password="test-pass-123",
        )

        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_delete_account_requires_authenticated_user(self):
        response = self.client.post("/api/v1/auth/delete-account", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"success": False})

    def test_delete_account_deletes_user_and_clears_session(self):
        user = User.objects.create_user(
            username="delete-me",
            email="delete-me@example.com",
            password="test-pass-123",
        )
        self.client.force_login(user)

        response = self.client.post("/api/v1/auth/delete-account", HTTP_HOST="localhost")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        self.assertFalse(User.objects.filter(id=user.id).exists())

        me_response = self.client.get("/api/v1/auth/me", HTTP_HOST="localhost")
        self.assertEqual(
            me_response.json(),
            {
                "authenticated": False,
                "user": None,
            },
        )
