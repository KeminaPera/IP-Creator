-- =============================================
-- Migration: 011_fix_lora_models_celery_fields
-- Description: Add missing Celery task tracking fields to lora_models
-- Date: 2026-05-24
-- 
-- This migration fixes incomplete migration 008 by adding:
-- 1. celery_task_id - Celery async task ID for training jobs
-- 2. retry_count - Number of training retries
-- 3. max_retries - Maximum retry attempts allowed
--
-- These fields are required by the ORM model but were missing
-- from the original migration script.
-- =============================================

-- Add missing columns to lora_models table
ALTER TABLE lora_models ADD COLUMN celery_task_id VARCHAR(255);
ALTER TABLE lora_models ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE lora_models ADD COLUMN max_retries INTEGER DEFAULT 2;

-- Create index for celery_task_id
CREATE INDEX IF NOT EXISTS idx_lora_celery_task ON lora_models(celery_task_id);

-- =============================================
-- Comments and Documentation
-- =============================================

-- New columns added to lora_models:
-- celery_task_id: Celery asynchronous task ID for tracking training jobs
-- retry_count: Current number of retry attempts (default: 0)
-- max_retries: Maximum allowed retry attempts (default: 2)

-- Usage examples:
-- 
-- 1. Get LoRA model with its Celery task:
--    SELECT id, name, celery_task_id, status FROM lora_models WHERE id = 1;
--
-- 2. Find failed tasks that can be retried:
--    SELECT * FROM lora_models 
--    WHERE status = 'failed' AND retry_count < max_retries;
--
-- 3. Update retry count:
--    UPDATE lora_models SET retry_count = retry_count + 1 WHERE id = 1;
