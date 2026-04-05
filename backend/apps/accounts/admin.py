from django.contrib import admin

from apps.accounts.models.user_profile import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "google_account_id", "onboarding_completed", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "google_account_id")
    list_filter = ("onboarding_completed",)
