-- Migration 006: Create workflows table for FlowPipe engine
-- Stores user-created workflow definitions as JSON

CREATE TABLE IF NOT EXISTS workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    workflow_json TEXT NOT NULL,
    is_default BOOLEAN DEFAULT 0,
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_workflows_is_default ON workflows(is_default);
CREATE INDEX IF NOT EXISTS idx_workflows_created_by ON workflows(created_by);
