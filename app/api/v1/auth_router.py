"""
Authentication API Router

Endpoints for user login, registration, and token management.
"""
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config.database import get_db_session
from app.models.user import User
from app.schemas.auth_schema import UserLogin, TokenResponse
from app.security.auth import auth_service
from app.core.exceptions import (
    UnauthorizedException,
    ForbiddenException,
    AppException
)
from app.utils.response import success_response
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login")
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Login and get JWT access token.
    
    Args:
        login_data: Login credentials
        db: Database session
        
    Returns:
        JWT access token and user info
        
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by username
    result = await db.execute(
        select(User).where(User.username == login_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise UnauthorizedException(
            message="Incorrect username or password",
            details={"username": login_data.username}
        )
    
    # Verify password
    if not auth_service.verify_password(login_data.password, user.hashed_password):
        raise UnauthorizedException(
            message="Incorrect username or password",
            details={"username": login_data.username}
        )
    
    # Check if user is active
    if not user.is_active:
        raise ForbiddenException(
            message="User account is disabled",
            details={"username": user.username}
        )
    
    # Create access token
    access_token = auth_service.create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    
    # Update login count
    user.login_count = (user.login_count or 0) + 1
    
    from datetime import datetime
    user.last_login = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"User {user.username} logged in successfully")
    
    return success_response(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "full_name": user.full_name,
            },
        },
        message="Login successful"
    )
