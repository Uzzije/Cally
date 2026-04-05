from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.services.user_profile_service import ensure_user_profile


User = get_user_model()


@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    if created:
        ensure_user_profile(instance)


@receiver(post_save, sender=SocialAccount)
def sync_profile_from_social_account(sender, instance, **kwargs):
    ensure_user_profile(instance.user, social_account=instance)
