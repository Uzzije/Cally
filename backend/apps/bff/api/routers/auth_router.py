import logging

from django.contrib.auth import logout
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from ninja import Router

from apps.core.api.auth import session_auth
from apps.bff.api.schemas.auth_me_response_schema import AuthMeResponseSchema
from apps.bff.api.schemas.auth_user_schema import AuthUserSchema
from apps.accounts.services.user_profile_service import ensure_user_profile

router = Router(tags=["auth"], auth=session_auth)
logger = logging.getLogger("apps.accounts.auth")


@router.get("csrf", auth=None)
@ensure_csrf_cookie
def get_csrf_token(request):
    logger.debug("auth.csrf_issued")
    return JsonResponse({"success": True})


@router.get("me", auth=None, response=AuthMeResponseSchema)
def get_authenticated_user(request):
    if not request.user.is_authenticated:
        logger.info("auth.session_bootstrap anonymous=true")
        return AuthMeResponseSchema(authenticated=False, user=None)

    profile = ensure_user_profile(request.user)
    display_name = request.user.get_full_name().strip() or request.user.email
    logger.info(
        "auth.session_bootstrap anonymous=false user_id=%s has_google_account=%s onboarding_completed=%s",
        request.user.id,
        bool(profile.google_account_id),
        profile.onboarding_completed,
    )

    return AuthMeResponseSchema(
        authenticated=True,
        user=AuthUserSchema(
            id=request.user.id,
            email=request.user.email,
            display_name=display_name,
            avatar_url=profile.avatar_url or None,
            has_google_account=bool(profile.google_account_id),
            onboarding_completed=profile.onboarding_completed,
        ),
    )


@router.post("logout")
def logout_authenticated_user(request):
    logger.info("auth.logout user_id=%s", request.user.id)
    logout(request)
    return {"success": True}


@router.post("onboarding/complete")
def complete_onboarding(request):
    profile = ensure_user_profile(request.user)
    if not profile.onboarding_completed:
        profile.onboarding_completed = True
        profile.save(update_fields=["onboarding_completed", "updated_at"])
        logger.info("auth.onboarding_complete user_id=%s updated=true", request.user.id)
    else:
        logger.info("auth.onboarding_complete user_id=%s updated=false", request.user.id)

    return {"success": True}


@router.post("delete-account")
@ratelimit(key="user_or_ip", rate="3/m", method=ratelimit.ALL, block=True)
def delete_authenticated_user(request):
    user = request.user
    user_id = user.id
    logout(request)
    user.delete()
    logger.info("auth.delete_account user_id=%s deleted=true", user_id)
    return {"success": True}
