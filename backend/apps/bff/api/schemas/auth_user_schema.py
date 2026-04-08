from ninja import Schema


class AuthUserSchema(Schema):
    id: int
    email: str
    display_name: str
    avatar_url: str | None = None
    has_google_account: bool
    onboarding_completed: bool
