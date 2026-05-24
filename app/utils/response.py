"""
Unified API Response Utilities

Standardized response format for all API endpoints.
All responses follow this structure:
{
    "success": true/false,
    "data": {...},              # optional (success only)
    "message": "...",           # optional
    "error": {...},             # optional (failure only)
    "pagination": {...},        # optional (list only)
    "meta": {...},              # optional
    "traceId": "..."            # always present (32-char hex)
}
"""
from typing import Any, Dict, List, Optional
from fastapi.responses import JSONResponse
from app.core.trace import get_trace_id


def _build_response_base(success: bool) -> Dict[str, Any]:
    """
    Build response base structure with traceId.
    
    Args:
        success: Whether the request was successful
    
    Returns:
        Dictionary with success and traceId fields
    """
    return {
        "success": success,
        "traceId": get_trace_id()  # Always include Trace ID
    }


def success_response(
    data: Any,
    message: Optional[str] = None,
    pagination: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Response format:
    {
        "success": true,
        "data": {...},
        "message": "...",           # optional
        "pagination": {...},        # optional
        "meta": {...},              # optional
        "traceId": "a1b2c3d4..."    # always present
    }
    
    Args:
        data: Response data (can be any type: object, array, primitive)
        message: Optional success message
        pagination: Optional pagination info (for list endpoints)
        meta: Optional additional metadata
        status_code: HTTP status code (default: 200)
    
    Returns:
        Dictionary with standardized response structure
    
    Example:
        return success_response(
            data={"id": 1, "name": "test"},
            message="Created successfully"
        )
    """
    response = _build_response_base(success=True)
    response["data"] = data
    
    if message is not None:
        response["message"] = message
    
    if pagination is not None:
        response["pagination"] = pagination
    
    if meta is not None:
        response["meta"] = meta
    
    return response


def list_response(
    items: List[Any],
    page: int,
    page_size: int,
    total: int,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized list response with pagination.
    
    Args:
        items: List of items
        page: Current page number (1-based)
        page_size: Items per page
        total: Total items count
        message: Optional success message
        meta: Optional additional metadata
    
    Returns:
        Dictionary with standardized list response structure
    
    Example:
        return list_response(
            items=users,
            page=page,
            page_size=page_size,
            total=total
        )
    """
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    pagination = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages
    }
    
    return success_response(
        data=items,
        message=message,
        pagination=pagination,
        meta=meta
    )


def created_response(
    data: Any,
    message: str = "Resource created successfully"
) -> Dict[str, Any]:
    """
    Create a standardized response for resource creation.
    
    Args:
        data: Created resource data
        message: Success message
    
    Returns:
        Dictionary with 201 status code
    
    Example:
        return created_response(
            data={"id": new_id},
            message="User created successfully"
        )
    """
    return success_response(data=data, message=message, status_code=201)


def updated_response(
    data: Any,
    message: str = "Resource updated successfully"
) -> Dict[str, Any]:
    """
    Create a standardized response for resource update.
    
    Args:
        data: Updated resource data
        message: Success message
    
    Returns:
        Dictionary with updated response
    
    Example:
        return updated_response(
            data={"id": 1, "name": "updated"},
            message="User updated successfully"
        )
    """
    return success_response(data=data, message=message)


def deleted_response(
    resource_id: Any,
    message: str = "Resource deleted successfully"
) -> Dict[str, Any]:
    """
    Create a standardized response for resource deletion.
    
    Args:
        resource_id: Deleted resource ID
        message: Success message
    
    Returns:
        Dictionary with deleted response
    
    Example:
        return deleted_response(
            resource_id=123,
            message="User deleted successfully"
        )
    """
    return success_response(
        data={"id": resource_id},
        message=message
    )


def message_response(
    message: str,
    data: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Create a simple message response (for operations without data).
    
    Args:
        message: Success message
        data: Optional data
    
    Returns:
        Dictionary with message response
    
    Example:
        return message_response(
            message="Task submitted successfully",
            data={"task_id": "12345"}
        )
    """
    return success_response(data=data or {}, message=message)


def error_response(
    error_type: str,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Any] = None,
    status_code: int = 500
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Response format:
    {
        "success": false,
        "message": "Error message",         # Top-level message
        "error": {
            "type": "ErrorType",            # Error type
            "code": "ERROR_CODE",           # optional: Machine-readable code
            "details": {...}                # optional: Error details
        },
        "traceId": "a1b2c3d4..."           # always present
    }
    
    Args:
        error_type: Error type (e.g., "ConflictError", "NotFoundError")
        message: Human-readable error message (shown at top level)
        error_code: Machine-readable error code (optional)
        details: Additional error details (optional)
        status_code: HTTP status code (default: 500)
    
    Returns:
        Dictionary with standardized error response structure
    
    Example:
        return error_response(
            error_type="ConflictError",
            message="Trigger word 'lulu' already exists",
            error_code="TRIGGER_WORD_EXISTS",
            details={"field": "trigger_word", "value": "lulu"},
            status_code=409
        )
    """
    response = _build_response_base(success=False)
    response["message"] = message  # Message at top level
    
    # Build error object
    error_obj = {
        "type": error_type
    }
    if error_code:
        error_obj["code"] = error_code
    if details:
        error_obj["details"] = details
    
    response["error"] = error_obj
    
    return response
