-- Migration: Create generated_contents table
-- Date: 2026-05-05
-- Description: Add content library table for managing generated stories, images, and videos

CREATE TABLE IF NOT EXISTS generated_contents (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Task Association
    task_id VARCHAR(100) UNIQUE,
    task_type VARCHAR(50) NOT NULL,
    
    -- Content Type & Metadata
    content_type VARCHAR(20) NOT NULL,
    title VARCHAR(200),
    description TEXT,
    
    -- File Storage
    file_path VARCHAR(500),
    thumbnail_path VARCHAR(500),
    file_size INTEGER,
    
    -- Media-specific Metadata
    duration_seconds INTEGER,
    resolution VARCHAR(20),
    word_count INTEGER,
    
    -- IP Asset Association
    ip_asset_id INTEGER REFERENCES ip_assets(id),
    
    -- Content Parameters
    parameters JSON,
    
    -- Content Metadata
    content_metadata JSON,
    
    -- Tagging & Organization
    tags JSON,
    is_favorite BOOLEAN DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT,
    
    -- Performance Metrics
    execution_time_seconds FLOAT,
    channel_id INTEGER,
    
    -- Metadata
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_generated_contents_content_type ON generated_contents(content_type);
CREATE INDEX IF NOT EXISTS idx_generated_contents_task_type ON generated_contents(task_type);
CREATE INDEX IF NOT EXISTS idx_generated_contents_ip_asset_id ON generated_contents(ip_asset_id);
CREATE INDEX IF NOT EXISTS idx_generated_contents_status ON generated_contents(status);
CREATE INDEX IF NOT EXISTS idx_generated_contents_created_at ON generated_contents(created_at);
CREATE INDEX IF NOT EXISTS idx_generated_contents_is_favorite ON generated_contents(is_favorite);
