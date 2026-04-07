from django.test import TestCase, RequestFactory
from django.http import HttpResponse

from django_ratelimit.exceptions import Ratelimited

from apps.core.api.rate_limit import rate_limited_response


class RateLimitedResponseTests(TestCase):
    """Tests for the custom rate-limited response view used by RatelimitMiddleware.

    django-ratelimit's middleware catches the Ratelimited exception and
    delegates to RATELIMIT_VIEW. Our view must return a 429 JSON body that
    matches the project's ErrorResponseSchema contract.
    """

    def setUp(self):
        self.factory = RequestFactory()

    def test_returns_429_status(self):
        request = self.factory.get("/api/v1/chat/credits")
        response = rate_limited_response(request, exception=Ratelimited())
        self.assertEqual(response.status_code, 429)

    def test_returns_json_content_type(self):
        request = self.factory.get("/api/v1/chat/credits")
        response = rate_limited_response(request, exception=Ratelimited())
        self.assertEqual(response["Content-Type"], "application/json")

    def test_body_contains_detail_key(self):
        import json

        request = self.factory.get("/api/v1/chat/credits")
        response = rate_limited_response(request, exception=Ratelimited())
        body = json.loads(response.content)
        self.assertIn("detail", body)

    def test_body_detail_message_describes_rate_limiting(self):
        import json

        request = self.factory.get("/api/v1/chat/credits")
        response = rate_limited_response(request, exception=Ratelimited())
        body = json.loads(response.content)
        self.assertIn("rate limit", body["detail"].lower())

    def test_includes_retry_after_header(self):
        request = self.factory.get("/api/v1/chat/credits")
        response = rate_limited_response(request, exception=Ratelimited())
        self.assertIn("Retry-After", response)
        self.assertTrue(int(response["Retry-After"]) > 0)
