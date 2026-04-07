from django.apps import apps
from django.test import SimpleTestCase


class PreferencesAppTests(SimpleTestCase):
    def test_preferences_app_is_installed(self):
        app_config = apps.get_app_config("preferences")

        self.assertEqual(app_config.name, "apps.preferences")
