"""
IP-Creator Database Initialization Script

This script initializes the database with:
1. Complete schema (all tables)
2. Seed data (providers and models)
3. Default admin user

Usage: python init_database.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.config.database import async_session_factory, engine
from app.models.user import User
from app.security.auth import auth_service
from app.utils.logger import logger


async def run_sql_file(filepath: str):
    """Execute SQL file."""
    print(f"\n📄 Executing: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    async with async_session_factory() as session:
        try:
            # Split by statements and execute
            statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
            
            for statement in statements:
                if statement:
                    await session.execute(text(statement))
            
            await session.commit()
            print(f"✅ Successfully executed {filepath}")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error executing {filepath}: {e}")
            raise


async def create_default_admin():
    """Create default admin user."""
    print("\n👤 Creating default admin user...")
    
    admin_username = "admin"
    admin_password = "admin123"
    admin_email = "admin@ipcreator.local"
    
    async with async_session_factory() as session:
        # Check if admin already exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.username == admin_username)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"ℹ️  Admin user '{admin_username}' already exists")
            return False
        
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
        
        print(f"✅ Default admin user created successfully!")
        print(f"   Username: {admin_username}")
        print(f"   Password: {admin_password}")
        return True


async def initialize_database():
    """Main initialization function."""
    print("\n" + "="*60)
    print("  IP-Creator Database Initialization")
    print("="*60)
    
    try:
        # Step 1: Create schema
        print("\n📋 Step 1: Creating database schema...")
        await run_sql_file('sql/schema_complete.sql')
        
        # Step 2: Insert seed data
        print("\n🌱 Step 2: Inserting seed data...")
        await run_sql_file('sql/seed_data.sql')
        
        # Step 3: Create admin user
        print("\n🔐 Step 3: Setting up admin user...")
        admin_created = await create_default_admin()
        
        # Summary
        print("\n" + "="*60)
        print("  ✅ Database Initialization Complete!")
        print("="*60)
        print("\n📊 Summary:")
        print("   ✓ Database schema created (8 tables)")
        print("   ✓ Seed data inserted (5 providers, 11 models)")
        if admin_created:
            print("   ✓ Admin user created")
        else:
            print("   ✓ Admin user already exists")
        
        print("\n📝 Next Steps:")
        print("   1. Start backend: python -m uvicorn app.main:app --reload --port 8000")
        print("   2. Start Celery: celery -A celery_worker.celery_app worker --loglevel=info --pool=solo")
        print("   3. Start frontend: cd frontend-vue && npm run dev")
        print("   4. Login at: http://localhost:5173/login")
        print("      Username: admin")
        print("      Password: admin123")
        
        print("\n⚠️  IMPORTANT:")
        print("   - Change the admin password in production!")
        print("   - Configure your LLM API keys in the admin panel")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("\n🔧 Starting database initialization...\n")
    asyncio.run(initialize_database())
