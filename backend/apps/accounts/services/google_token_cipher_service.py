from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


class GoogleTokenCipherService:
    def __init__(self) -> None:
        self._fernet = Fernet(self._build_key())

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")

    def _build_key(self) -> bytes:
        configured_key = getattr(settings, "GOOGLE_TOKEN_ENCRYPTION_KEY", "") or ""
        if configured_key:
            return configured_key.encode("utf-8")

        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)
