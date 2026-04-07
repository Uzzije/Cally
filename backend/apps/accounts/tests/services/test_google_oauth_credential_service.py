from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import TestCase

from apps.accounts.models.google_oauth_credential import GoogleOAuthCredential
from apps.accounts.services.google_oauth_credential_service import GoogleOAuthCredentialService

User = get_user_model()


class GoogleOAuthCredentialServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ignored",
            email="credential-service@example.com",
            password="test-pass-123",
        )
        site = Site.objects.get_current()
        social_app = SocialApp.objects.create(
            provider="google",
            name="Google",
            client_id="client-id",
            secret="client-secret",
        )
        social_app.sites.add(site)
        social_account = SocialAccount.objects.create(
            user=self.user,
            provider="google",
            uid="google-user-1",
        )
        self.social_token = SocialToken.objects.create(
            app=social_app,
            account=social_account,
            token="plain-access-token",
            token_secret="plain-refresh-token",
        )

    def test_sync_from_social_token_encrypts_and_redacts_plaintext_tokens(self):
        service = GoogleOAuthCredentialService()

        credential = service.sync_from_social_token(self.social_token)

        assert credential is not None
        self.social_token.refresh_from_db()
        self.assertEqual(self.social_token.token, "")
        self.assertEqual(self.social_token.token_secret, "")
        self.assertNotEqual(credential.access_token_encrypted, "plain-access-token")
        self.assertNotEqual(credential.refresh_token_encrypted, "plain-refresh-token")
        decrypted = service.get_decrypted_credential(self.user)
        self.assertEqual(decrypted.access_token, "plain-access-token")
        self.assertEqual(decrypted.refresh_token, "plain-refresh-token")

    def test_get_decrypted_credential_bootstraps_existing_plaintext_social_token_once(self):
        service = GoogleOAuthCredentialService()

        decrypted = service.get_decrypted_credential(self.user)

        self.assertEqual(decrypted.access_token, "plain-access-token")
        self.assertTrue(GoogleOAuthCredential.objects.filter(user=self.user).exists())
        self.social_token.refresh_from_db()
        self.assertEqual(self.social_token.token, "")
