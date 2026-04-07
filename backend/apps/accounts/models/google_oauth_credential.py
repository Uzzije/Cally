from django.conf import settings
from django.db import models


class GoogleOAuthCredential(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_oauth_credential",
    )
    google_account_id = models.CharField(max_length=255, blank=True)
    access_token_encrypted = models.TextField(blank=True)
    refresh_token_encrypted = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_google_oauth_credential"

    def __str__(self) -> str:
        return f"GoogleOAuthCredential<{self.user_id}>"
