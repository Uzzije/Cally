from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


class GoogleTokenCipherService:
    def __init__(self) -> None:
        """Encrypt/decrypt Google OAuth tokens using a stable Fernet key."""
        self._fernet = Fernet(self._build_key())

    def encrypt(self, value: str) -> str:
        """Encrypt a plaintext token into a URL-safe string."""
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        """Decrypt a previously encrypted token (or raise if the ciphertext is invalid)."""
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")

    def _build_key(self) -> bytes:
        """Derive the Fernet key from explicit config or fallback to SECRET_KEY."""
        configured_key = getattr(settings, "GOOGLE_TOKEN_ENCRYPTION_KEY", "") or ""
        if configured_key:
            return configured_key.encode("utf-8")

        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)
