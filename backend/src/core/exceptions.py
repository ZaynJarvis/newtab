"""Custom exceptions and error handling for Local Web Memory Backend."""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
import traceback

from src.core.logging import get_logger


logger = get_logger(__name__)


class LocalWebMemoryException(Exception):
    """Base exception for Local Web Memory application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        super().__init__(message)


class DatabaseException(LocalWebMemoryException):
    """Exception raised for database-related errors."""
    
    def __init__(self, message: str, operation: str = None, **kwargs):
        super().__init__(message, error_code="DATABASE_ERROR", **kwargs)
        if operation:
            self.details["operation"] = operation


class APIClientException(LocalWebMemoryException):
    """Exception raised for external API client errors."""
    
    def __init__(self, message: str, service: str = None, status_code: int = None, **kwargs):
        super().__init__(message, error_code="API_CLIENT_ERROR", **kwargs)
        if service:
            self.details["service"] = service
        if status_code:
            self.details["status_code"] = status_code


class VectorStoreException(LocalWebMemoryException):
    """Exception raised for vector store errors."""
    
    def __init__(self, message: str, operation: str = None, **kwargs):
        super().__init__(message, error_code="VECTOR_STORE_ERROR", **kwargs)
        if operation:
            self.details["operation"] = operation


class ValidationException(LocalWebMemoryException):
    """Exception raised for data validation errors."""
    
    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        if field:
            self.details["field"] = field
        if value is not None:
            self.details["value"] = str(value)


class AuthenticationException(LocalWebMemoryException):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kwargs)


class AuthorizationException(LocalWebMemoryException):
    """Exception raised for authorization errors."""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", **kwargs)


class RateLimitException(LocalWebMemoryException):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None, **kwargs):
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)
        if retry_after:
            self.details["retry_after"] = retry_after


class ConfigurationException(LocalWebMemoryException):
    """Exception raised for configuration errors."""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        super().__init__(message, error_code="CONFIGURATION_ERROR", **kwargs)
        if config_key:
            self.details["config_key"] = config_key


def create_error_response(
    status_code: int,
    message: str,
    error_code: str = "UNKNOWN_ERROR",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """Create a standardized error response."""
    error_data = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": logger._context.get("timestamp") if hasattr(logger, "_context") else None
        }
    }
    
    if details:
        error_data["error"]["details"] = details
    
    if request_id:
        error_data["error"]["request_id"] = request_id
    
    return JSONResponse(
        status_code=status_code,
        content=error_data,
        headers={"X-Request-ID": request_id} if request_id else None
    )


async def local_web_memory_exception_handler(request: Request, exc: LocalWebMemoryException):
    """Handle LocalWebMemoryException and return structured error response."""
    # Log the exception
    logger.error(
        f"Application exception: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "exception_type": type(exc).__name__,
            "url": str(request.url),
            "method": request.method
        },
        exc_info=exc.cause if exc.cause else True
    )
    
    # Record error metric
    try:
        from src.api.monitoring import record_error_metric
        record_error_metric(exc.error_code)
    except ImportError:
        pass  # Monitoring module may not be available
    
    # Determine HTTP status code based on exception type
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    if isinstance(exc, ValidationException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, AuthenticationException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, AuthorizationException):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, RateLimitException):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(exc, (DatabaseException, VectorStoreException)):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, APIClientException):
        # Use the status code from the API client exception if available
        status_code = exc.details.get("status_code", status.HTTP_502_BAD_GATEWAY)
    elif isinstance(exc, ConfigurationException):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    # Get request ID if available
    request_id = getattr(request.state, "request_id", None)
    
    return create_error_response(
        status_code=status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=request_id
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions and return structured error response."""
    # Log the exception
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "url": str(request.url),
            "method": request.method,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    # Record error metric
    try:
        from src.api.monitoring import record_error_metric
        record_error_metric("UNHANDLED_EXCEPTION")
    except ImportError:
        pass  # Monitoring module may not be available
    
    # Get request ID if available
    request_id = getattr(request.state, "request_id", None)
    
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred",
        error_code="INTERNAL_SERVER_ERROR",
        request_id=request_id
    )


async def http_exception_handler_with_logging(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler with logging."""
    # Log HTTP exceptions
    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "url": str(request.url),
            "method": request.method,
            "headers": dict(exc.headers) if exc.headers else None
        }
    )
    
    # Record error metric
    try:
        from src.api.monitoring import record_error_metric
        record_error_metric(f"HTTP_{exc.status_code}")
    except ImportError:
        pass  # Monitoring module may not be available
    
    # Get request ID if available
    request_id = getattr(request.state, "request_id", None)
    
    # Create structured response
    if exc.status_code >= 400:
        return create_error_response(
            status_code=exc.status_code,
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}",
            request_id=request_id
        )
    
    # For non-error HTTP responses, use the default handler
    return await http_exception_handler(request, exc)


async def validation_exception_handler(request: Request, exc: Exception):
    """Handle Pydantic validation exceptions."""
    logger.warning(
        "Validation error",
        extra={
            "url": str(request.url),
            "method": request.method,
            "validation_errors": str(exc)
        }
    )
    
    # Record error metric
    try:
        from src.api.monitoring import record_error_metric
        record_error_metric("VALIDATION_ERROR")
    except ImportError:
        pass  # Monitoring module may not be available
    
    # Get request ID if available
    request_id = getattr(request.state, "request_id", None)
    
    # Extract validation details if it's a Pydantic validation error
    details = None
    if hasattr(exc, "errors"):
        details = {"validation_errors": exc.errors()}
    
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        error_code="VALIDATION_ERROR",
        details=details,
        request_id=request_id
    )


def handle_database_error(operation: str, error: Exception) -> None:
    """Handle database errors and raise appropriate exception."""
    error_msg = f"Database operation '{operation}' failed: {str(error)}"
    logger.error(error_msg, extra={"operation": operation}, exc_info=True)
    raise DatabaseException(error_msg, operation=operation, cause=error)


def handle_api_client_error(service: str, operation: str, error: Exception, status_code: int = None) -> None:
    """Handle API client errors and raise appropriate exception."""
    error_msg = f"API call to {service}.{operation} failed: {str(error)}"
    logger.error(error_msg, extra={"service": service, "operation": operation}, exc_info=True)
    raise APIClientException(error_msg, service=service, status_code=status_code, cause=error)


def handle_vector_store_error(operation: str, error: Exception) -> None:
    """Handle vector store errors and raise appropriate exception."""
    error_msg = f"Vector store operation '{operation}' failed: {str(error)}"
    logger.error(error_msg, extra={"operation": operation}, exc_info=True)
    raise VectorStoreException(error_msg, operation=operation, cause=error)


def validate_required_field(value: Any, field_name: str) -> None:
    """Validate that a required field is not None or empty."""
    if value is None:
        raise ValidationException(f"Field '{field_name}' is required", field=field_name)
    
    if isinstance(value, str) and not value.strip():
        raise ValidationException(f"Field '{field_name}' cannot be empty", field=field_name, value=value)


def validate_url(url: str, field_name: str = "url") -> None:
    """Validate URL format."""
    if not url or not isinstance(url, str):
        raise ValidationException(f"Invalid URL format", field=field_name, value=url)
    
    # Basic URL validation
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValidationException(f"URL must start with http:// or https://", field=field_name, value=url)


def validate_page_id(page_id: Any, field_name: str = "page_id") -> int:
    """Validate page ID format."""
    try:
        page_id_int = int(page_id)
        if page_id_int <= 0:
            raise ValidationException(f"Page ID must be a positive integer", field=field_name, value=page_id)
        return page_id_int
    except (ValueError, TypeError):
        raise ValidationException(f"Invalid page ID format", field=field_name, value=page_id)


# Export commonly used functions and exceptions
__all__ = [
    'LocalWebMemoryException',
    'DatabaseException',
    'APIClientException', 
    'VectorStoreException',
    'ValidationException',
    'AuthenticationException',
    'AuthorizationException',
    'RateLimitException',
    'ConfigurationException',
    'create_error_response',
    'local_web_memory_exception_handler',
    'general_exception_handler',
    'http_exception_handler_with_logging',
    'validation_exception_handler',
    'handle_database_error',
    'handle_api_client_error',
    'handle_vector_store_error',
    'validate_required_field',
    'validate_url',
    'validate_page_id'
]