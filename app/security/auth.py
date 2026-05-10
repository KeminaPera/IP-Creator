"""
Authentication Service

Handles user authentication, password hashing, JWT token
generation, and role-based access control.
"""
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config.settings import settings
from app.utils.logger import logger


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Service for authentication and authorization.
    
    Provides password hashing, JWT token management,
    and user authentication utilities.
    """
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Token payload data
            expires_delta: Token expiration time
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        
        return encoded_jwt
    
    def decode_access_token(self, token: str) -> Optional[dict]:
        """
        Decode and validate JWT access token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None
    
    def authenticate_user(self, username: str, password: str, user) -> Optional[dict]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: Username
            password: Password
            user: User object from database
            
        Returns:
            User data if authenticated, None otherwise
        """
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
        }


# Global auth service instance
auth_service = AuthService()
