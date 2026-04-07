from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from allauth.socialaccount.models import SocialToken
from django.utils import timezone

from apps.accounts.models.google_oauth_credential import GoogleOAuthCredential
from apps.accounts.services.google_token_cipher_service import GoogleTokenCipherService
from apps.core.types import AuthenticatedUser


class GoogleOAuthCredentialError(Exception):
    pass


@dataclass(frozen=True)
class DecryptedGoogleOAuthCredential:
    access_token: str
    refresh_token: str
    expires_at: datetime | None


class GoogleOAuthCredentialService:
    def __init__(self, cipher: GoogleTokenCipherService | None = None) -> None:
        self.cipher = cipher or GoogleTokenCipherService()

    def has_credential(self, user: AuthenticatedUser) -> bool:
        credential = self._load_or_bootstrap(user)
        return bool(
            credential and credential.access_token_encrypted and credential.refresh_token_encrypted
        )

    def get_decrypted_credential(self, user: AuthenticatedUser) -> DecryptedGoogleOAuthCredential:
        credential = self._load_or_bootstrap(user)
        if credential is None or not credential.access_token_encrypted:
            raise GoogleOAuthCredentialError("Google access token is not available.")

        refresh_token = ""
        if credential.refresh_token_encrypted:
            refresh_token = self.cipher.decrypt(credential.refresh_token_encrypted)

        return DecryptedGoogleOAuthCredential(
            access_token=self.cipher.decrypt(credential.access_token_encrypted),
            refresh_token=refresh_token,
            expires_at=credential.expires_at,
        )

    def sync_from_social_token(self, social_token: SocialToken) -> GoogleOAuthCredential | None:
        if social_token.account.provider != "google":
            return None
        if not social_token.token and not social_token.token_secret:
            return GoogleOAuthCredential.objects.filter(user=social_token.account.user).first()

        credential, _ = GoogleOAuthCredential.objects.update_or_create(
            user=social_token.account.user,
            defaults={
                "google_account_id": social_token.account.uid or "",
                "access_token_encrypted": self.cipher.encrypt(social_token.token or ""),
                "refresh_token_encrypted": self.cipher.encrypt(social_token.token_secret or ""),
                "expires_at": social_token.expires_at,
            },
        )
        if social_token.token or social_token.token_secret:
            social_token.token = ""
            social_token.token_secret = ""
            social_token.save(update_fields=["token", "token_secret"])
        return credential

    def update_access_token(
        self,
        user: AuthenticatedUser,
        *,
        access_token: str,
        expires_at,
    ) -> GoogleOAuthCredential:
        credential = self._load_or_bootstrap(user)
        if credential is None:
            raise GoogleOAuthCredentialError("Google refresh token is not available.")
        credential.access_token_encrypted = self.cipher.encrypt(access_token)
        credential.expires_at = expires_at
        credential.save(update_fields=["access_token_encrypted", "expires_at", "updated_at"])
        return credential

    def _load_or_bootstrap(self, user: AuthenticatedUser) -> GoogleOAuthCredential | None:
        credential = GoogleOAuthCredential.objects.filter(user=user).first()
        if credential is not None:
            return credential

        social_token = (
            SocialToken.objects.select_related("account")
            .filter(account__user=user, account__provider="google")
            .first()
        )
        if social_token is None:
            return None
        return self.sync_from_social_token(social_token)
