import importlib
import os
import sys
from unittest import TestCase
from unittest.mock import patch


class BaseSettingsTests(TestCase):
    def _load_base_settings(self, env: dict[str, str]):
        with patch.dict(os.environ, env, clear=True):
            sys.modules.pop("config.settings", None)
            sys.modules.pop("config.settings.base", None)
            return importlib.import_module("config.settings.base")

    def test_requires_secret_key_in_production_like_runtime(self):
        with self.assertRaisesRegex(
            ValueError,
            "DJANGO_SECRET_KEY must be set when DJANGO_ENV is production-like.",
        ):
            self._load_base_settings(
                {
                    "DJANGO_ENV": "production",
                    "DJANGO_DEBUG": "false",
                }
            )

    def test_defaults_debug_to_false_in_production_like_runtime(self):
        settings_module = self._load_base_settings(
            {
                "DJANGO_ENV": "production",
                "DJANGO_SECRET_KEY": "production-secret-key",
            }
        )

        self.assertFalse(settings_module.DEBUG)

    def test_defaults_timezone_to_utc(self):
        settings_module = self._load_base_settings({})

        self.assertEqual(settings_module.TIME_ZONE, "UTC")

    def test_google_oauth_scopes_can_disable_gmail_permissions(self):
        settings_module = self._load_base_settings(
            {
                "GOOGLE_OAUTH_ENABLE_GMAIL_ACTIONS": "false",
            }
        )

        scopes = settings_module.SOCIALACCOUNT_PROVIDERS["google"]["SCOPE"]

        self.assertNotIn("https://www.googleapis.com/auth/gmail.send", scopes)
        self.assertNotIn("https://www.googleapis.com/auth/gmail.compose", scopes)
