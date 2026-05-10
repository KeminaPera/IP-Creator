"""
Test migration scripts for training dataset tables.

This script executes the migration SQL files and verifies the tables are created correctly.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.config.database import async_session_factory, engine


async def test_migrations():
    """Test migration scripts."""
    print("=" * 60)
    print("Testing Migration Scripts")
    print("=" * 60)
    
    migration_files = [
        "sql/migrations/006_create_training_datasets.sql",
        "sql/migrations/007_create_test_images_and_checkpoints.sql",
        "sql/migrations/008_extend_lora_models.sql",
    ]
    
    async with async_session_factory() as session:
        for migration_file in migration_files:
            filepath = Path(migration_file)
            
            if not filepath.exists():
                print(f"\n❌ Migration file not found: {migration_file}")
                continue
            
            print(f"\n📄 Executing: {migration_file}")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # Split by statements and execute
                statements = [
                    s.strip() 
                    for s in sql_content.split(';') 
                    if s.strip() and not s.strip().startswith('--')
                ]
                
                for statement in statements:
                    if statement:
                        await session.execute(text(statement))
                
                await session.commit()
                print(f"✅ Successfully executed {migration_file}")
                
            except Exception as e:
                await session.rollback()
                print(f"❌ Error executing {migration_file}: {e}")
                raise
        
        # Verify tables were created
        print("\n" + "=" * 60)
        print("Verifying Tables")
        print("=" * 60)
        
        tables_to_check = [
            'training_datasets',
            'dataset_images',
            'test_images',
            'training_checkpoints',
        ]
        
        for table in tables_to_check:
            try:
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                count = result.scalar()
                print(f"✅ Table '{table}' exists (rows: {count})")
            except Exception as e:
                print(f"❌ Table '{table}' check failed: {e}")
        
        # Verify lora_models extensions
        print("\n" + "=" * 60)
        print("Verifying lora_models Extensions")
        print("=" * 60)
        
        try:
            result = await session.execute(
                text("PRAGMA table_info(lora_models)")
            )
            columns = result.fetchall()
            
            new_columns = ['dataset_id', 'quality_score', 'quality_report', 'recommended_checkpoint_id']
            existing_columns = [col[1] for col in columns]
            
            for col_name in new_columns:
                if col_name in existing_columns:
                    print(f"✅ Column '{col_name}' added to lora_models")
                else:
                    print(f"❌ Column '{col_name}' NOT found in lora_models")
                    
        except Exception as e:
            print(f"❌ Error checking lora_models: {e}")
        
        # Check indexes
        print("\n" + "=" * 60)
        print("Verifying Indexes")
        print("=" * 60)
        
        tables_with_indexes = [
            'training_datasets',
            'dataset_images',
            'test_images',
            'training_checkpoints',
            'lora_models',
        ]
        
        for table in tables_with_indexes:
            try:
                result = await session.execute(
                    text(f"PRAGMA index_list({table})")
                )
                indexes = result.fetchall()
                print(f"✅ Table '{table}' has {len(indexes)} indexes")
            except Exception as e:
                print(f"❌ Error checking indexes for '{table}': {e}")
    
    print("\n" + "=" * 60)
    print("✅ Migration Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_migrations())
