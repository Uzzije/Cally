from django.test import SimpleTestCase, override_settings

from apps.calendars.services.calendar_webhook_address_resolver_service import (
    CalendarWebhookAddressResolverService,
)


class CalendarWebhookAddressResolverServiceTests(SimpleTestCase):
    @override_settings(
        GOOGLE_CALENDAR_WEBHOOK_ADDRESS="https://example.com/api/v1/calendar/webhook/google"
    )
    def test_prefers_explicit_webhook_address(self):
        resolved = CalendarWebhookAddressResolverService().resolve()

        self.assertEqual(resolved, "https://example.com/api/v1/calendar/webhook/google")

    @override_settings(
        GOOGLE_CALENDAR_WEBHOOK_ADDRESS="", BACKEND_PUBLIC_BASE_URL="https://api.example.com"
    )
    def test_derives_webhook_address_from_public_backend_base_url(self):
        resolved = CalendarWebhookAddressResolverService().resolve()

        self.assertEqual(resolved, "https://api.example.com/api/v1/calendar/webhook/google")

    @override_settings(
        DEBUG=False,
        GOOGLE_CALENDAR_WEBHOOK_ADDRESS="http://example.com/api/v1/calendar/webhook/google",
        BACKEND_PUBLIC_BASE_URL="",
    )
    def test_rejects_insecure_non_https_webhook_address_in_non_debug_mode(self):
        resolved = CalendarWebhookAddressResolverService().resolve()

        self.assertIsNone(resolved)
