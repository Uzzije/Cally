from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from apps.core.api.auth import session_auth

User = get_user_model()


class SessionAuthTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="session-auth-test",
            email="session-auth@example.com",
            password="test-pass-123",
        )

    def _build_request(self, user=None):
        request = self.factory.get("/fake")
        request.user = user if user is not None else self.user
        return request

    def test_returns_user_for_authenticated_request(self):
        request = self._build_request(user=self.user)
        result = session_auth(request)
        self.assertEqual(result, self.user)

    def test_returns_none_for_anonymous_request(self):
        from django.contrib.auth.models import AnonymousUser

        request = self._build_request(user=AnonymousUser())
        result = session_auth(request)
        self.assertIsNone(result)
