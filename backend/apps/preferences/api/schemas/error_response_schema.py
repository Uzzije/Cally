from ninja import Schema


class ErrorResponseSchema(Schema):
    detail: str
    errors: dict[str, list[str]] | None = None
