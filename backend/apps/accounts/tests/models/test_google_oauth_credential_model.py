from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models.google_oauth_credential import GoogleOAuthCredential

User = get_user_model()


class GoogleOAuthCredentialModelTests(TestCase):
    def test_enforces_one_google_credential_record_per_user(self):
        user = User.objects.create_user(
            username="ignored",
            email="credential-model@example.com",
            password="test-pass-123",
        )
        GoogleOAuthCredential.objects.create(user=user)

        with self.assertRaises(IntegrityError):
            GoogleOAuthCredential.objects.create(user=user)
