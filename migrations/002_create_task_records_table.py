import asyncio
from sqlalchemy import text
from app.config.database import get_db_session


async def upgrade():
    """
    Create task_records table for asynchronous task tracking.
    """
    print("Creating task_records table...")
    
    async for db in get_db_session():
        try:
            # Create task_records table
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS task_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    task_type TEXT NOT NULL,
                    ip_asset_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0.0,
                    parameters TEXT,
                    priority INTEGER DEFAULT 0,
                    result_path TEXT,
                    result_metadata TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    gpu_memory_used REAL,
                    execution_time_seconds REAL,
                    created_by INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ip_asset_id) REFERENCES ip_assets(id)
                )
            """))
            
            # Create indexes for better performance
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_task_records_status ON task_records(status)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_task_records_type ON task_records(task_type)"))
            await db.execute(text("CREATE INDEX IF NOT EXISTS idx_task_records_ip ON task_records(ip_asset_id)"))
            
            await db.commit()
            print("✓ Successfully created task_records table")
            
        except Exception as e:
            await db.rollback()
            print(f"✗ Error creating task_records table: {e}")
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
