from typing import Any


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=422, error_code="VALIDATION_ERROR", details=details)


class AuthenticationException(AppException):
    def __init__(
        self, message: str = "Authentication failed", details: dict[str, Any] | None = None
    ):
        super().__init__(
            message, status_code=401, error_code="AUTHENTICATION_ERROR", details=details
        )


class AuthorizationException(AppException):
    def __init__(self, message: str = "Not authorized", details: dict[str, Any] | None = None):
        super().__init__(
            message, status_code=403, error_code="AUTHORIZATION_ERROR", details=details
        )


class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: str | int, details: dict[str, Any] | None = None):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, status_code=404, error_code="NOT_FOUND", details=details)


class ConflictException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=409, error_code="CONFLICT", details=details)


class RateLimitException(AppException):
    def __init__(self, message: str = "Rate limit exceeded", details: dict[str, Any] | None = None):
        super().__init__(
            message, status_code=429, error_code="RATE_LIMIT_EXCEEDED", details=details
        )


class ExternalServiceException(AppException):
    def __init__(self, service: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            f"{service} error: {message}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details,
        )


class AIServiceException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=500, error_code="AI_SERVICE_ERROR", details=details)


class VectorStoreException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=500, error_code="VECTOR_STORE_ERROR", details=details)


class DocumentProcessingException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message, status_code=500, error_code="DOCUMENT_PROCESSING_ERROR", details=details
        )
