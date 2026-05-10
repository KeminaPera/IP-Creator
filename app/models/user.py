"""
User Model

Manages user authentication and role-based access control
for system security and permission management.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.config.database import Base


class User(Base):
    """
    User account management with role-based permissions.
    
    Supports admin and regular user roles with different
    access levels to system features and resources.
    """
    __tablename__ = "users"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # User Credentials
    username = Column(String(50), nullable=False, unique=True, index=True, comment="Login username")
    email = Column(String(100), nullable=True, unique=True, index=True, comment="User email address")
    hashed_password = Column(String(255), nullable=False, comment="Bcrypt hashed password")
    
    # User Profile
    full_name = Column(String(100), nullable=True, comment="Display name")
    avatar_path = Column(String(500), nullable=True, comment="Profile avatar path")
    
    # Role & Permissions
    role = Column(String(20), default="user", index=True, comment="admin or user")
    permissions = Column(JSON, nullable=True, comment="Granular permissions list")
    is_active = Column(Boolean, default=True, index=True, comment="Whether account is active")
    
    # Security
    last_login = Column(DateTime(timezone=True), nullable=True, index=True, comment="Last login timestamp")
    login_count = Column(Integer, default=0, comment="Total login count")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Account creation time")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Update timestamp")
    
    # Composite Indexes
    __table_args__ = (
        # Active users by role: filter by role, active status
        Index('idx_user_role_active', 'role', 'is_active'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
