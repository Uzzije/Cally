from ninja import Schema

from apps.bff.api.schemas.auth_user_schema import AuthUserSchema


class AuthMeResponseSchema(Schema):
    authenticated: bool
    user: AuthUserSchema | None = None
