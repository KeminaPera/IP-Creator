-- =============================================
-- IP-Creator Database Schema
-- Database: SQLite
-- Description: Complete database schema for IP-Creator system
-- Created: 2026-04-30
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

-- Comments (SQLite doesn't support comments on columns, documented here)
-- id: Primary Key
-- username: Login username (unique)
-- email: User email address (unique)
-- hashed_password: Bcrypt hashed password
-- full_name: Display name
-- avatar_path: Profile avatar path
-- role: admin or user
-- permissions: Granular permissions list (JSON)
-- is_active: Whether account is active
-- last_login: Last login timestamp
-- login_count: Total login count
-- created_at: Account creation time
-- updated_at: Update timestamp


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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_llm_providers_code ON llm_providers(code);
CREATE INDEX IF NOT EXISTS idx_llm_providers_active ON llm_providers(is_active);

-- Comments
-- id: Primary Key
-- code: Unique identifier (e.g., openai, zhipu, ollama) - UNIQUE
-- name_cn: Chinese name
-- name_en: English name
-- icon_class: Font Awesome icon class (e.g., fa-brands fa-openai)
-- icon_url: Icon image path (e.g., /static/images/providers/openai.svg)
-- website: Official website
-- api_docs_url: API documentation URL
-- default_endpoint: Default API endpoint
-- requires_api_key: Whether API key is required
-- api_key_pattern: API key format regex for validation
-- is_active: Whether provider is available
-- is_recommended: Whether provider is recommended
-- sort_order: Display order in dropdowns
-- description_cn: Chinese description
-- description_en: English description
-- created_at: Creation timestamp
-- updated_at: Update timestamp


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

-- Comments
-- id: Primary Key
-- provider_id: Associated provider ID (Foreign Key)
-- code: Model unique identifier (e.g., gpt-4o, glm-4)
-- name: Model display name
-- version: Version number (e.g., 2.0, 3.5)
-- capabilities: ["text_generation", "vision", "code", "chat"] (JSON)
-- max_tokens: Maximum context length
-- max_output_tokens: Maximum output length
-- supports_streaming: Supports streaming output
-- supports_function_calling: Supports function calling
-- supports_vision: Supports vision/image input
-- input_price_per_million: Input price per million tokens
-- output_price_per_million: Output price per million tokens
-- speed_rating: Speed rating 1-5
-- quality_rating: Quality rating 1-5
-- is_active: Whether model is available
-- is_recommended: Whether model is recommended
-- sort_order: Display order in dropdowns
-- release_date: Release date
-- deprecated_date: Deprecation date
-- description: Model description
-- created_at: Creation timestamp
-- updated_at: Update timestamp
-- CONSTRAINT uq_provider_model: UNIQUE (provider_id, code) - Prevents duplicate models under same provider


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

-- Comments
-- id: Primary Key
-- name: Display name for the model/channel
-- model_type: local or cloud
-- provider: ollama, openai, zhipu, qwen, etc.
-- model_name: Actual model identifier
-- api_endpoint: API endpoint URL for cloud models
-- api_key_encrypted: Encrypted API key for cloud models
-- local_path: Local model path for local models
-- temperature: Sampling temperature
-- max_tokens: Maximum tokens to generate
-- timeout: Request timeout in seconds
-- context_window: Context window size
-- additional_params: Additional model-specific parameters (JSON)
-- is_active: Whether model is available for use
-- is_default: Default model for the system
-- health_status: healthy, unhealthy, unknown
-- last_health_check: Last health check time
-- response_time_ms: Average response time in milliseconds
-- success_rate: Success rate percentage
-- description: Model description
-- created_at: Creation timestamp
-- updated_at: Update timestamp

-- ⚠️ NOTE: This table NOW has a unique constraint to prevent duplicate channels
-- Multiple channels CANNOT be created with the same provider + model_name combination
-- Constraint: uq_provider_model_name UNIQUE (provider, model_name)


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

-- Comments
-- id: Primary Key
-- name: LoRA model name
-- file_path: Path to .safetensors file
-- base_model: Base model used for training
-- training_params: Training parameters used (JSON)
--   Format: {"epochs": 10, "learning_rate": 1e-4, "batch_size": 4, ...}
-- final_loss: Final training loss
-- training_steps: Total training steps
-- training_time_minutes: Total training time
-- status: training, completed, failed, archived
-- error_message: Error details if training failed
-- weight_default: Default inference weight (0.0-1.0)
-- is_active: Whether model is available for use
-- description: Model description
-- created_at: Creation timestamp
-- updated_at: Update timestamp


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

-- Comments
-- id: Primary Key
-- name: IP character name
-- category: Category: pet, human, fantasy, etc.
-- description: IP character description
-- reference_images: List of image paths with angles (JSON)
--   Format: [{"angle": "front", "path": "/path/to/image.jpg"}, ...]
-- positive_tags: Positive style tags (JSON)
-- negative_tags: Negative tags to avoid (JSON)
-- trigger_word: Unique trigger word for this IP
-- style_template: Preset style: 3d_cartoon, blind_box, healing, etc.
-- lora_model_id: Associated LoRA model ID (Foreign Key)
-- created_at: Creation timestamp
-- updated_at: Update timestamp


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

-- Comments
-- id: Primary Key
-- task_id: Celery task ID (UNIQUE)
-- task_type: lora_training, image_gen, video_gen, post_process
-- ip_asset_id: Associated IP asset ID (Foreign Key)
-- status: pending, running, completed, failed, cancelled
-- progress: Progress percentage (0-100)
-- parameters: Task input parameters (JSON)
-- priority: Task priority (higher = more important)
-- result_path: Path to generated output
-- result_metadata: Additional result information (JSON)
-- error_message: Error details if failed
-- retry_count: Number of retry attempts
-- gpu_memory_used: GPU memory used in GB
-- execution_time_seconds: Total execution time
-- created_by: User ID who created the task
-- created_at: Creation timestamp
-- started_at: Task start time
-- completed_at: Task completion time


-- =============================================
-- Database Schema Summary
-- =============================================
-- Total Tables: 7
-- 
-- Table List:
-- 1. users              - User authentication and role management
-- 2. llm_providers      - LLM provider configurations (OpenAI, Zhipu, etc.)
-- 3. llm_models         - LLM model versions per provider
-- 4. llm_configs        - LLM channel configurations (active instances)
-- 5. lora_models        - Trained LoRA fine-tuned models
-- 6. ip_assets          - IP character assets and reference images
-- 7. task_records       - Async task tracking and audit trail
--
-- Relationships:
-- - llm_models.provider_id → llm_providers.id (CASCADE DELETE)
-- - ip_assets.lora_model_id → lora_models.id (SET NULL)
-- - task_records.ip_asset_id → ip_assets.id (SET NULL)
--
-- Unique Constraints:
-- - users.username (UNIQUE)
-- - users.email (UNIQUE)
-- - llm_providers.code (UNIQUE)
-- - llm_models.provider_id + code (UNIQUE - prevents duplicate models per provider)
-- - llm_configs.provider + model_name (UNIQUE - prevents duplicate channels)
-- - task_records.task_id (UNIQUE)
-- =============================================
