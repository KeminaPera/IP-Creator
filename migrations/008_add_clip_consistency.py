"""
Migration 008: Add clip_consistency column to quality_reports table

Adds CLIP character consistency score field to quality reports.
"""
import sqlite3
from pathlib import Path

def upgrade():
    """Add clip_consistency column to quality_reports table."""
    db_path = Path("data/ip_creator.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(quality_reports)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "clip_consistency" not in columns:
            print("Adding clip_consistency column to quality_reports...")
            cursor.execute("""
                ALTER TABLE quality_reports
                ADD COLUMN clip_consistency FLOAT
            """)
            conn.commit()
            print("✅ clip_consistency column added successfully")
        else:
            print("⏭️  clip_consistency column already exists")
    
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def downgrade():
    """Remove clip_consistency column (SQLite doesn't support DROP COLUMN easily)."""
    print("⚠️  SQLite doesn't support DROP COLUMN easily.")
    print("To downgrade, you would need to recreate the table without the column.")


if __name__ == "__main__":
    print("Running migration 008: Add clip_consistency to quality_reports")
    upgrade()
    print("Migration completed!")
