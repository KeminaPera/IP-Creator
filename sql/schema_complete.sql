-- =============================================
-- IP-Creator Database Schema
-- Database: SQLite
-- Description: Complete database schema for IP-Creator system
-- Version: 2.0
-- Created: 2026-04-30
-- Updated: 2026-05-05
-- =============================================

-- =============================================
-- 1. User Management Table
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_path VARCHAR(500),
    role VARCHAR(20) DEFAULT 'user',
    permissions JSON,
    is_active BOOLEAN DEFAULT 1,
    last_login DATETIME,
    login_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);


-- =============================================
-- 2. LLM Provider Table
-- =============================================
CREATE TABLE IF NOT EXISTS llm_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) NOT NULL UNIQUE,
    name_cn VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    icon_class VARCHAR(100),
    icon_url VARCHAR(500),
    website VARCHAR(500),
    api_docs_url VARCHAR(500),
    default_endpoint VARCHAR(500),
    requires_api_key BOOLEAN DEFAULT 1,
    api_key_pattern VARCHAR(200),
    is_active BOOLEAN DEFAULT 1,
    is_recommended BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    description_cn TEXT,
    description_en TEXT,
    last_synced_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_llm_providers_code ON llm_providers(code);
CREATE INDEX IF NOT EXISTS idx_llm_providers_active ON llm_providers(is_active);


-- =============================================
-- 3. LLM Model Table
-- =============================================
CREATE TABLE IF NOT EXISTS llm_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    version VARCHAR(50),
    capabilities JSON,
    max_tokens INTEGER,
    max_output_tokens INTEGER,
    supports_streaming BOOLEAN DEFAULT 1,
    supports_function_calling BOOLEAN DEFAULT 0,
    supports_vision BOOLEAN DEFAULT 0,
    input_price_per_million REAL,
    output_price_per_million REAL,
    speed_rating INTEGER,
    quality_rating INTEGER,
    is_active BOOLEAN DEFAULT 1,
    is_recommended BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    release_date DATE,
    deprecated_date DATE,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key
    FOREIGN KEY (provider_id) REFERENCES llm_providers(id) ON DELETE CASCADE,
    
    -- Unique Constraint: Prevent duplicate models under same provider
    CONSTRAINT uq_provider_model UNIQUE (provider_id, code)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_llm_models_provider ON llm_models(provider_id);
CREATE INDEX IF NOT EXISTS idx_llm_models_active ON llm_models(is_active);
CREATE INDEX IF NOT EXISTS idx_llm_models_code ON llm_models(code);


-- =============================================
-- 4. LLM Configuration (Channel) Table
-- =============================================
CREATE TABLE IF NOT EXISTS llm_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    model_type VARCHAR(20) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    api_endpoint VARCHAR(500),
    api_key_encrypted TEXT,
    local_path VARCHAR(500),
    temperature REAL DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2048,
    timeout INTEGER DEFAULT 60,
    context_window INTEGER DEFAULT 4096,
    additional_params JSON,
    is_active BOOLEAN DEFAULT 1,
    is_default BOOLEAN DEFAULT 0,
    health_status VARCHAR(20) DEFAULT 'unknown',
    last_health_check DATETIME,
    response_time_ms REAL,
    success_rate REAL DEFAULT 100.0,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique Constraint: Prevent duplicate channels for same provider + model
    CONSTRAINT uq_provider_model_name UNIQUE (provider, model_name)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_llm_configs_name ON llm_configs(name);
CREATE INDEX IF NOT EXISTS idx_llm_configs_provider ON llm_configs(provider);
CREATE INDEX IF NOT EXISTS idx_llm_configs_model_type ON llm_configs(model_type);
CREATE INDEX IF NOT EXISTS idx_llm_configs_active ON llm_configs(is_active);


-- =============================================
-- 5. LoRA Model Table
-- =============================================
CREATE TABLE IF NOT EXISTS lora_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    base_model VARCHAR(100) NOT NULL,
    training_params JSON,
    final_loss REAL,
    training_steps INTEGER,
    training_time_minutes REAL,
    status VARCHAR(20) DEFAULT 'training',
    error_message TEXT,
    weight_default REAL DEFAULT 0.7,
    is_active BOOLEAN DEFAULT 1,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_lora_models_name ON lora_models(name);
CREATE INDEX IF NOT EXISTS idx_lora_models_status ON lora_models(status);
CREATE INDEX IF NOT EXISTS idx_lora_models_active ON lora_models(is_active);
CREATE INDEX IF NOT EXISTS idx_lora_models_base_model ON lora_models(base_model);


-- =============================================
-- 6. IP Asset Table
-- =============================================
CREATE TABLE IF NOT EXISTS ip_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    description TEXT,
    reference_images JSON NOT NULL,
    positive_tags JSON,
    negative_tags JSON,
    trigger_word VARCHAR(100) NOT NULL,
    style_template VARCHAR(50),
    lora_model_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key
    FOREIGN KEY (lora_model_id) REFERENCES lora_models(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ip_assets_name ON ip_assets(name);
CREATE INDEX IF NOT EXISTS idx_ip_assets_trigger_word ON ip_assets(trigger_word);
CREATE INDEX IF NOT EXISTS idx_ip_assets_category ON ip_assets(category);
CREATE INDEX IF NOT EXISTS idx_ip_assets_lora_model_id ON ip_assets(lora_model_id);


-- =============================================
-- 7. Task Record Table
-- =============================================
CREATE TABLE IF NOT EXISTS task_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(100) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL,
    ip_asset_id INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    progress REAL DEFAULT 0.0,
    parameters JSON,
    priority INTEGER DEFAULT 0,
    result_path VARCHAR(500),
    result_metadata JSON,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    gpu_memory_used REAL,
    execution_time_seconds REAL,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    
    -- Foreign Key
    FOREIGN KEY (ip_asset_id) REFERENCES ip_assets(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_task_records_task_id ON task_records(task_id);
CREATE INDEX IF NOT EXISTS idx_task_records_task_type ON task_records(task_type);
CREATE INDEX IF NOT EXISTS idx_task_records_status ON task_records(status);
CREATE INDEX IF NOT EXISTS idx_task_records_ip_asset_id ON task_records(ip_asset_id);
CREATE INDEX IF NOT EXISTS idx_task_records_created_at ON task_records(created_at);


-- =============================================
-- 8. Generated Content Table (Content Library)
-- =============================================
CREATE TABLE IF NOT EXISTS generated_contents (
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
    ip_asset_id INTEGER,
    
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key
    FOREIGN KEY (ip_asset_id) REFERENCES ip_assets(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_generated_contents_content_type ON generated_contents(content_type);
CREATE INDEX IF NOT EXISTS idx_generated_contents_task_type ON generated_contents(task_type);
CREATE INDEX IF NOT EXISTS idx_generated_contents_ip_asset_id ON generated_contents(ip_asset_id);
CREATE INDEX IF NOT EXISTS idx_generated_contents_status ON generated_contents(status);
CREATE INDEX IF NOT EXISTS idx_generated_contents_created_at ON generated_contents(created_at);
CREATE INDEX IF NOT EXISTS idx_generated_contents_is_favorite ON generated_contents(is_favorite);


-- =============================================
-- Database Schema Summary
-- =============================================
-- Total Tables: 8
-- 
-- Table List:
-- 1. users                - User authentication and role management
-- 2. llm_providers        - LLM provider configurations (OpenAI, Zhipu, etc.)
-- 3. llm_models           - LLM model versions per provider
-- 4. llm_configs          - LLM channel configurations (active instances)
-- 5. lora_models          - Trained LoRA fine-tuned models
-- 6. ip_assets            - IP character assets and reference images
-- 7. task_records         - Async task tracking and audit trail
-- 8. generated_contents   - Content library for generated stories, images, videos
--
-- Relationships:
-- - llm_models.provider_id → llm_providers.id (CASCADE DELETE)
-- - ip_assets.lora_model_id → lora_models.id (SET NULL)
-- - task_records.ip_asset_id → ip_assets.id (SET NULL)
-- - generated_contents.ip_asset_id → ip_assets.id (SET NULL)
--
-- Unique Constraints:
-- - users.username (UNIQUE)
-- - users.email (UNIQUE)
-- - llm_providers.code (UNIQUE)
-- - llm_models.provider_id + code (UNIQUE)
-- - llm_configs.provider + model_name (UNIQUE)
-- - task_records.task_id (UNIQUE)
-- - generated_contents.task_id (UNIQUE)
-- =============================================
