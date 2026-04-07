import importlib
import os
from unittest.mock import patch

from django.test import SimpleTestCase

from config.settings import base as base_settings


class FrontendAuthSettingsTests(SimpleTestCase):
    def reload_settings(self, env: dict[str, str]):
        with patch.dict(os.environ, env, clear=True):
            module = importlib.reload(base_settings)

        self.addCleanup(importlib.reload, base_settings)
        return module

    def test_headless_frontend_urls_default_to_local_frontend_routes(self):
        settings_module = self.reload_settings({})

        self.assertEqual(settings_module.FRONTEND_BASE_URL, "http://localhost:3002")
        self.assertEqual(
            settings_module.HEADLESS_FRONTEND_URLS["account_confirm_email"],
            "http://localhost:3002/auth/verify-email/{key}",
        )
        self.assertEqual(
            settings_module.HEADLESS_FRONTEND_URLS["socialaccount_login_error"],
            "http://localhost:3002/auth/error",
        )

    def test_headless_frontend_urls_follow_frontend_base_url(self):
        settings_module = self.reload_settings(
            {"FRONTEND_BASE_URL": "https://tenex-frontend.onrender.com"}
        )

        self.assertEqual(
            settings_module.HEADLESS_FRONTEND_URLS["account_confirm_email"],
            "https://tenex-frontend.onrender.com/auth/verify-email/{key}",
        )
        self.assertEqual(
            settings_module.HEADLESS_FRONTEND_URLS["account_reset_password"],
            "https://tenex-frontend.onrender.com/auth/password/reset",
        )
        self.assertEqual(
            settings_module.LOGIN_REDIRECT_URL,
            "https://tenex-frontend.onrender.com",
        )
        self.assertEqual(
            settings_module.LOGOUT_REDIRECT_URL,
            "https://tenex-frontend.onrender.com",
        )

    def test_explicit_frontend_auth_overrides_take_precedence(self):
        settings_module = self.reload_settings(
            {
                "FRONTEND_BASE_URL": "https://tenex-frontend.onrender.com",
                "FRONTEND_AUTH_ERROR_URL": "https://app.example.com/login/error",
            }
        )

        self.assertEqual(
            settings_module.HEADLESS_FRONTEND_URLS["socialaccount_login_error"],
            "https://app.example.com/login/error",
        )
        self.assertEqual(
            settings_module.HEADLESS_FRONTEND_URLS["account_signup"],
            "https://tenex-frontend.onrender.com/auth/signup",
        )

    def test_cookie_samesite_defaults_to_lax(self):
        settings_module = self.reload_settings({})

        self.assertEqual(settings_module.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings_module.CSRF_COOKIE_SAMESITE, "Lax")

    def test_cookie_samesite_can_be_overridden_for_cross_site_deployments(self):
        settings_module = self.reload_settings(
            {
                "DJANGO_SESSION_COOKIE_SAMESITE": "None",
                "DJANGO_CSRF_COOKIE_SAMESITE": "None",
            }
        )

        self.assertEqual(settings_module.SESSION_COOKIE_SAMESITE, "None")
        self.assertEqual(settings_module.CSRF_COOKIE_SAMESITE, "None")

    def test_invalid_cookie_samesite_value_raises_error(self):
        with self.assertRaisesMessage(
            ValueError,
            "DJANGO_SESSION_COOKIE_SAMESITE must be one of: Lax, None, Strict",
        ):
            self.reload_settings({"DJANGO_SESSION_COOKIE_SAMESITE": "invalid"})
