"""
Initialize Default Admin User

Run this script to create a default admin account.
Usage: python init_admin.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.config.database import async_session_factory
from app.models.user import User
from app.security.auth import auth_service
from app.utils.logger import logger


async def create_default_admin():
    """Create default admin user if not exists."""
    
    admin_username = "admin"
    admin_password = "admin123"  # Change this in production!
    admin_email = "admin@ipcreator.local"
    
    async with async_session_factory() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.username == admin_username)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            logger.info(f"Admin user '{admin_username}' already exists")
            print(f"\n✅ Admin user already exists!")
            print(f"   Username: {admin_username}")
            print(f"   Password: (unchanged)")
            return
        
        # Create admin user
        hashed_password = auth_service.hash_password(admin_password)
        
        admin_user = User(
            username=admin_username,
            email=admin_email,
            hashed_password=hashed_password,
            full_name="System Administrator",
            role="admin",
            is_active=True,
        )
        
        session.add(admin_user)
        await session.commit()
        
        logger.info(f"Default admin user created: {admin_username}")
        print(f"\n✅ Default admin user created successfully!")
        print(f"\n{'='*50}")
        print(f"   Username: {admin_username}")
        print(f"   Password: {admin_password}")
        print(f"{'='*50}")
        print(f"\n⚠️  IMPORTANT: Change this password in production!")
        print(f"   You can login at: http://localhost:8000/login")


if __name__ == "__main__":
    print("\n🔧 Initializing default admin user...\n")
    asyncio.run(create_default_admin())
