from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.services.google_oauth_credential_service import GoogleOAuthCredentialService
from apps.accounts.services.user_profile_service import ensure_user_profile

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    if created:
        ensure_user_profile(instance)


@receiver(post_save, sender=SocialAccount)
def sync_profile_from_social_account(sender, instance, **kwargs):
    ensure_user_profile(instance.user, social_account=instance)


@receiver(post_save, sender=SocialToken)
def sync_google_oauth_credential_from_social_token(sender, instance, **kwargs):
    GoogleOAuthCredentialService().sync_from_social_token(instance)
