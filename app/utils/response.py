"""
Unified API Response Utilities

Standardized response format for all API endpoints.
All responses follow this structure:
{
    "success": true,
    "data": {...},
    "message": "...",        # optional
    "pagination": {...},     # optional (list only)
    "meta": {...}            # optional
}
"""
from typing import Any, Dict, List, Optional
from fastapi.responses import JSONResponse


def success_response(
    data: Any,
    message: Optional[str] = None,
    pagination: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
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
    response = {
        "success": True,
        "data": data
    }
    
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
