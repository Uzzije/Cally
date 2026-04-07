class PreferencesValidationError(Exception):
    def __init__(self, detail: str, *, errors: dict[str, list[str]] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.errors = errors or {}
