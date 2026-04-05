from ninja import Schema


class ErrorResponseSchema(Schema):
    detail: str

