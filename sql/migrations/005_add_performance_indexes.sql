-- Migration: 005_add_performance_indexes
-- Description: Add optimized indexes to all tables for improved query performance
-- Date: 2026-05-06
--
-- This migration adds indexes to improve performance for:
-- - Content library filtering and sorting (generated_contents)
-- - Task monitoring queries (task_records)
-- - IP asset management (ip_assets)
-- - LoRA model queries (lora_models)
-- - LLM configuration lookups (llm_configs)
-- - User authentication and management (users)

-- ==========================================
-- generated_contents table indexes
-- ==========================================

-- Single column indexes for common filters
CREATE INDEX IF NOT EXISTS idx_content_status ON generated_contents(status);
CREATE INDEX IF NOT EXISTS idx_content_created_at ON generated_contents(created_at);
CREATE INDEX IF NOT EXISTS idx_content_updated_at ON generated_contents(updated_at);
CREATE INDEX IF NOT EXISTS idx_content_is_favorite ON generated_contents(is_favorite);
CREATE INDEX IF NOT EXISTS idx_content_channel_id ON generated_contents(channel_id);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_content_status_type_created ON generated_contents(status, content_type, created_at);
CREATE INDEX IF NOT EXISTS idx_content_ip_status_created ON generated_contents(ip_asset_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_content_favorite_created ON generated_contents(is_favorite, created_at);
CREATE INDEX IF NOT EXISTS idx_content_task_type_status ON generated_contents(task_type, status, created_at);

-- ==========================================
-- task_records table indexes
-- ==========================================

-- Single column indexes for task monitoring
CREATE INDEX IF NOT EXISTS idx_task_status ON task_records(status);
CREATE INDEX IF NOT EXISTS idx_task_created_at ON task_records(created_at);
CREATE INDEX IF NOT EXISTS idx_task_started_at ON task_records(started_at);
CREATE INDEX IF NOT EXISTS idx_task_completed_at ON task_records(completed_at);

-- Composite indexes for task queries
CREATE INDEX IF NOT EXISTS idx_task_ip_status_created ON task_records(ip_asset_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_task_status_created ON task_records(status, created_at);
CREATE INDEX IF NOT EXISTS idx_task_channel_status ON task_records(channel_id, status);

-- ==========================================
-- ip_assets table indexes
-- ==========================================

-- Single column indexes for IP management
CREATE INDEX IF NOT EXISTS idx_ip_updated_at ON ip_assets(updated_at);
CREATE INDEX IF NOT EXISTS idx_ip_category ON ip_assets(category);
CREATE INDEX IF NOT EXISTS idx_ip_lora_model_id ON ip_assets(lora_model_id);

-- Composite indexes for IP queries
CREATE INDEX IF NOT EXISTS idx_ip_category_updated ON ip_assets(category, updated_at);
CREATE INDEX IF NOT EXISTS idx_ip_lora_updated ON ip_assets(lora_model_id, updated_at);

-- ==========================================
-- lora_models table indexes
-- ==========================================

-- Single column indexes for model queries
CREATE INDEX IF NOT EXISTS idx_lora_status ON lora_models(status);
CREATE INDEX IF NOT EXISTS idx_lora_is_active ON lora_models(is_active);
CREATE INDEX IF NOT EXISTS idx_lora_created_at ON lora_models(created_at);
CREATE INDEX IF NOT EXISTS idx_lora_base_model ON lora_models(base_model);

-- Composite indexes for model queries
CREATE INDEX IF NOT EXISTS idx_lora_status_active_created ON lora_models(status, is_active, created_at);
CREATE INDEX IF NOT EXISTS idx_lora_base_status ON lora_models(base_model, status);

-- ==========================================
-- llm_configs table indexes (legacy)
-- ==========================================

-- Single column indexes for LLM lookups
CREATE INDEX IF NOT EXISTS idx_llm_is_active ON llm_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_llm_is_default ON llm_configs(is_default);
CREATE INDEX IF NOT EXISTS idx_llm_health_status ON llm_configs(health_status);
CREATE INDEX IF NOT EXISTS idx_llm_model_type ON llm_configs(model_type);
CREATE INDEX IF NOT EXISTS idx_llm_provider ON llm_configs(provider);

-- Composite indexes for LLM queries
CREATE INDEX IF NOT EXISTS idx_llm_type_provider_active ON llm_configs(model_type, provider, is_active);
CREATE INDEX IF NOT EXISTS idx_llm_health_updated ON llm_configs(health_status, updated_at);

-- ==========================================
-- users table indexes
-- ==========================================

-- Single column indexes for user management
CREATE INDEX IF NOT EXISTS idx_user_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_user_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_user_last_login ON users(last_login);

-- Composite indexes for user queries
CREATE INDEX IF NOT EXISTS idx_user_role_active ON users(role, is_active);
