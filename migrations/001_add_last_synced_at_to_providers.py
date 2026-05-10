import asyncio
from sqlalchemy import text
from app.config.database import get_db_session


async def upgrade():
    """
    Add last_synced_at column to llm_providers table
    """
    print("Adding last_synced_at column to llm_providers table...")
    
    async for db in get_db_session():
        try:
            # Add the column
            await db.execute(text("""
                ALTER TABLE llm_providers 
                ADD COLUMN last_synced_at TIMESTAMP WITH TIME ZONE NULL
            """))
            
            # Update existing records with current timestamp
            await db.execute(text("""
                UPDATE llm_providers SET last_synced_at = datetime('now')
            """))
            
            await db.commit()
            print("✓ Successfully added last_synced_at column")
            
        except Exception as e:
            await db.rollback()
            print(f"✗ Error adding last_synced_at column: {e}")
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(upgrade())
    except Exception as e:
        print(f"Error running migration: {e}")
        import traceback
        traceback.print_exc()
