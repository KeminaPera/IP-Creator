"""
Simple test for migration scripts using direct SQLite.
"""
import sqlite3
from pathlib import Path

def test_migrations():
    """Test migration scripts using direct SQLite connection."""
    print("=" * 60)
    print("Testing Migration Scripts")
    print("=" * 60)
    
    db_path = Path("data/ip_creator.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    migration_files = [
        "sql/migrations/006_create_training_datasets.sql",
        "sql/migrations/007_create_test_images_and_checkpoints.sql",
        "sql/migrations/008_extend_lora_models.sql",
    ]
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        for migration_file in migration_files:
            filepath = Path(migration_file)
            
            if not filepath.exists():
                print(f"\n❌ Migration file not found: {migration_file}")
                continue
            
            print(f"\n📄 Executing: {migration_file}")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            try:
                cursor.executescript(sql_content)
                print(f"✅ Successfully executed {migration_file}")
            except Exception as e:
                print(f"❌ Error executing {migration_file}: {e}")
                raise
        
        # Verify tables
        print("\n" + "=" * 60)
        print("Verifying Tables")
        print("=" * 60)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'training_datasets',
            'dataset_images',
            'test_images',
            'training_checkpoints',
        ]
        
        for table in expected_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✅ Table '{table}' exists (rows: {count})")
            else:
                print(f"❌ Table '{table}' NOT found")
        
        # Verify lora_models columns
        print("\n" + "=" * 60)
        print("Verifying lora_models Extensions")
        print("=" * 60)
        
        cursor.execute("PRAGMA table_info(lora_models)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = ['dataset_id', 'quality_score', 'quality_report', 'recommended_checkpoint_id']
        
        for col_name in new_columns:
            if col_name in columns:
                print(f"✅ Column '{col_name}' added to lora_models")
            else:
                print(f"❌ Column '{col_name}' NOT found in lora_models")
        
        # Verify indexes
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
            cursor.execute(f"PRAGMA index_list({table})")
            indexes = cursor.fetchall()
            print(f"✅ Table '{table}' has {len(indexes)} indexes")
        
        print("\n" + "=" * 60)
        print("✅ Migration Test Complete")
        print("=" * 60)
        
    finally:
        conn.close()


if __name__ == "__main__":
    test_migrations()
