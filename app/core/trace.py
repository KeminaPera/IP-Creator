"""
Trace ID Management and Middleware for Request Tracking
========================================================

Provides async-safe Trace ID storage, retrieval, and middleware injection.
All Trace IDs are 32-character hexadecimal strings (UUID4 hex format).

Features:
1. Generate 32-character hex Trace IDs (UUID4)
2. Async-safe context storage using ContextVar
3. FastAPI middleware for automatic Trace ID injection
4. Automatic logging with Trace ID
5. Response header injection (X-Trace-ID)

Usage:
    # In middleware
    from app.core.trace import TraceIDMiddleware
    app.add_middleware(TraceIDMiddleware)
    
    # Anywhere in request lifecycle
    from app.core.trace import get_trace_id, generate_trace_id
    trace_id = get_trace_id()
"""
import uuid
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.utils.logger import logger


# ============================================================================
# Trace ID Context Management
# ============================================================================

# Async-safe Trace ID context variable
_trace_id_context: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    """
    Generate a new 32-character Trace ID.
    
    Uses UUID4 complete hex representation (32 hexadecimal characters).
    
    Returns:
        32-character hexadecimal string
        
    Examples:
        >>> generate_trace_id()
        'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
    """
    return uuid.uuid4().hex


def set_trace_id(trace_id: str) -> None:
    """
    Set the Trace ID for the current request context.
    
    Args:
        trace_id: 32-character hexadecimal Trace ID string
    """
    _trace_id_context.set(trace_id)


def get_trace_id() -> str:
    """
    Get the Trace ID for the current request context.
    
    Returns:
        32-character hexadecimal Trace ID string,
        or empty string if not set
    """
    return _trace_id_context.get()


def has_trace_id() -> bool:
    """
    Check if a Trace ID has been set for the current context.
    
    Returns:
        True if Trace ID is set, False otherwise
    """
    return bool(_trace_id_context.get())


# ============================================================================
# Trace ID Middleware
# ============================================================================

class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    Trace ID Middleware
    
    Injects a unique Trace ID into each request for distributed tracing.
    The Trace ID is:
    - Generated from request header (X-Trace-ID) or auto-generated
    - Stored in async-safe ContextVar
    - Added to response header (X-Trace-ID)
    - Logged with every log message (auto-injected by log format)
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Extract or generate Trace ID
        trace_id = (
            request.headers.get("x-trace-id") or  # From frontend (lowercase)
            request.headers.get("X-Trace-ID") or  # From frontend (uppercase)
            generate_trace_id()                    # Auto-generate
        )
        
        # 2. Set to context (async-safe)
        set_trace_id(trace_id)
        request.state.trace_id = trace_id  # Also store in request.state
        
        # 3. Log request start (Trace ID auto-injected by log format)
        client_host = request.client.host if request.client else "unknown"
        logger.info(
            f"← {request.method} {request.url.path} "
            f"from {client_host}"
        )
        
        # 4. Process request
        response = await call_next(request)
        
        # 5. Add Trace ID to response header
        response.headers["X-Trace-ID"] = trace_id
        
        # 6. Log response (Trace ID auto-injected by log format)
        content_length = response.headers.get("content-length", "?")
        logger.info(
            f"→ {response.status_code} "
            f"({content_length} bytes)"
        )
        
        return response
