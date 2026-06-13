"""
Unified Error Handling System

Provides consistent error response models and exception handlers
across the entire API.

All error responses follow this unified format:
{
    "success": false,
    "message": "Error message",
    "error": {
        "type": "ErrorType",
        "code": "ERROR_CODE",
        "details": {...}
    },
    "traceId": "a1b2c3d4..."
}
"""
from typing import Optional, Any
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.utils.logger import logger
from app.utils.response import error_response


# ==========================================
# Custom Exception Classes
# ==========================================

class AppException(HTTPException):
    """
    Base application exception with unified error structure.
    
    All custom exceptions should inherit from this class.
    """
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error: str = "InternalServerError",
        message: str = "An internal server error occurred",
        code: Optional[str] = None,
        details: Optional[Any] = None
    ):
        self.error_type = error
        self.error_code = code
        self.error_details = details
        
        super().__init__(
            status_code=status_code,
            detail=message  # FastAPI will handle this, but we override in handler
        )


class NotFoundException(AppException):
    """Resource not found (404)."""
    def __init__(self, resource: str = "Resource", identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with identifier '{identifier}' not found"
        
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error="NotFoundError",
            message=message,
            code=f"{resource.upper()}_NOT_FOUND"
        )


class BadRequestException(AppException):
    """Bad request (400)."""
    def __init__(self, message: str = "Bad request", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="BadRequestError",
            message=message,
            code="BAD_REQUEST",
            details=details
        )


class UnauthorizedException(AppException):
    """Unauthorized access (401)."""
    def __init__(self, message: str = "Invalid credentials", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="UnauthorizedError",
            message=message,
            code="UNAUTHORIZED",
            details=details
        )


class ForbiddenException(AppException):
    """Forbidden access (403)."""
    def __init__(self, message: str = "Access denied", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error="ForbiddenError",
            message=message,
            code="FORBIDDEN",
            details=details
        )


class ConflictException(AppException):
    """Resource conflict (409)."""
    def __init__(self, message: str = "Resource conflict", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error="ConflictError",
            message=message,
            code="CONFLICT",
            details=details
        )


class ValidationException(AppException):
    """Validation error (422)."""
    def __init__(self, message: str = "Validation error", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="ValidationError",
            message=message,
            code="VALIDATION_ERROR",
            details=details
        )


class InternalServerError(AppException):
    """Internal server error (500)."""
    def __init__(self, message: str = "Internal server error", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="InternalServerError",
            message=message,
            code="INTERNAL_ERROR",
            details=details
        )


# ==========================================
# Exception Handlers
# ==========================================

async def app_exception_handler(request: Request, exc: AppException):
    """
    Handle custom AppException with unified error response.
    
    Response format:
    {
        "success": false,
        "message": "Error detail",
        "error": {
            "type": "AppException error_type",
            "code": "AppException error_code",
            "details": {...}
        },
        "traceId": "current_trace_id"
    }
    """
    # Log with full exception details for server errors
    if exc.status_code >= 500:
        logger.error(
            f"AppException: {exc.error_type} - {exc.detail} "
            f"[{request.method} {request.url.path}] "
            f"Status: {exc.status_code}",
            exc_info=True  # Include full traceback
        )
    else:
        logger.warning(
            f"AppException: {exc.error_type} - {exc.detail} "
            f"[{request.method} {request.url.path}] "
            f"Status: {exc.status_code}"
        )
    
    # Build unified error response
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            error_type=exc.error_type,
            message=exc.detail,
            error_code=exc.error_code,
            details=exc.error_details,
            status_code=exc.status_code
        )
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle standard FastAPI HTTPException with unified error response.
    """
    # Determine error type from status code
    error_type_map = {
        400: "BadRequestError",
        401: "UnauthorizedError",
        403: "ForbiddenError",
        404: "NotFoundError",
        405: "MethodNotAllowedError",
        409: "ConflictError",
        422: "ValidationError",
        429: "RateLimitError",
        500: "InternalServerError",
        502: "BadGatewayError",
        503: "ServiceUnavailableError",
    }
    
    error_type = error_type_map.get(exc.status_code, "HTTPError")
    
    logger.warning(
        f"HTTPException: {exc.status_code} - {exc.detail} "
        f"[{request.method} {request.url.path}]"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            error_type=error_type,
            message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            error_code=f"HTTP_{exc.status_code}",
            status_code=exc.status_code
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with detailed error messages.
    """
    # Extract validation errors
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    logger.warning(
        f"Validation error: {validation_errors} "
        f"[{request.method} {request.url.path}]"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            error_type="ValidationError",
            message="Request validation failed",
            error_code="VALIDATION_ERROR",
            details=validation_errors,
            status_code=422
        )
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions with 500 error.
    
    This is the final catch-all handler for any unexpected exceptions.
    Internal details are NOT exposed to the client for security.
    """
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)} "
        f"[{request.method} {request.url.path}]",
        exc_info=True  # Include stack trace in logs
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            error_type="InternalServerError",
            message="An unexpected error occurred. Please try again later.",
            error_code="INTERNAL_ERROR",
            status_code=500
        )
    )


# ==========================================
# Helper Functions
# ==========================================

def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.
    
    Call this in main.py after creating the FastAPI app.
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
