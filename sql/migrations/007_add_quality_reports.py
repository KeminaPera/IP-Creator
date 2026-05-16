"""
Migration: Add quality_reports table

Creates the quality_reports table for storing LoRA model quality assessments.
"""
from sqlalchemy import text
from app.config.database import engine


def upgrade():
    """Create quality_reports table."""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS quality_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lora_id INTEGER NOT NULL,
        overall_score FLOAT NOT NULL,
        grade VARCHAR(2) NOT NULL,
        loss_score FLOAT,
        completion_score FLOAT,
        file_score FLOAT,
        generation_success FLOAT,
        test_images JSON,
        recommendations JSON,
        assessment_method VARCHAR(50) DEFAULT 'automated',
        status VARCHAR(20) DEFAULT 'completed',
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (lora_id) REFERENCES lora_models(id)
    );
    """
    
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_quality_reports_lora ON quality_reports(lora_id);",
        "CREATE INDEX IF NOT EXISTS idx_quality_reports_grade ON quality_reports(grade);",
        "CREATE INDEX IF NOT EXISTS idx_quality_reports_score ON quality_reports(overall_score);",
    ]
    
    with engine.begin() as conn:
        conn.execute(text(create_table_sql))
        for idx_sql in create_indexes_sql:
            conn.execute(text(idx_sql))
    
    print("✅ Created quality_reports table with indexes")


def downgrade():
    """Drop quality_reports table."""
    
    drop_sql = "DROP TABLE IF EXISTS quality_reports;"
    
    with engine.begin() as conn:
        conn.execute(text(drop_sql))
    
    print("✅ Dropped quality_reports table")


if __name__ == "__main__":
    upgrade()
