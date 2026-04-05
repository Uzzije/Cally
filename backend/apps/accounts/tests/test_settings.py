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
