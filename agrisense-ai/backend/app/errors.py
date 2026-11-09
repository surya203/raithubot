class AppError(Exception):
    """Error that maps to an HTTP response without including secrets."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    def __init__(self, message: str = "Record not found.") -> None:
        super().__init__(message, status_code=404)


class ConfigurationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)


class IntegrationError(AppError):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message, status_code=status_code)
