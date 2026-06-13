"""API dependencies package."""
from typing import Generator
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from app.security.auth import auth_service
from app.config.settings import settings
from app.utils.logger import logger
from app.core.exceptions import UnauthorizedException, ForbiddenException

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    FastAPI dependency to get current authenticated user.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        User data dictionary
        
    Raises:
        UnauthorizedException: If authentication fails
    """
    token = credentials.credentials
    
    payload = auth_service.decode_access_token(token)
    if payload is None:
        raise UnauthorizedException(
            message="Invalid authentication credentials",
            details={"token": "invalid"}
        )
    
    username = payload.get("sub")
    if username is None:
        raise UnauthorizedException(
            message="Invalid authentication credentials",
            details={"sub": "missing"}
        )
    
    # Fetch user from database
    from app.models.user import User
    from sqlalchemy import select
    
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise UnauthorizedException(
            message="User not found or inactive",
            details={"username": username}
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
    }


async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    FastAPI dependency to require admin role.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        User data if admin
        
    Raises:
        ForbiddenException: If user is not admin
    """
    role = current_user.get("role", "")
    if role not in ("admin", "super_admin"):
        raise ForbiddenException(
            message="Admin privileges required",
            details={"required_role": "admin", "current_role": role}
        )
    
    return current_user
