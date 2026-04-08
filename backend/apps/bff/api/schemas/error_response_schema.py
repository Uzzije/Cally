from pydantic import model_serializer
from ninja import Schema


class ErrorResponseSchema(Schema):
    detail: str
    code: str | None = None
    errors: dict[str, list[str]] | None = None

    @model_serializer(mode="wrap")
    def _exclude_none(self, handler):
        result = handler(self)
        return {k: v for k, v in result.items() if v is not None}
