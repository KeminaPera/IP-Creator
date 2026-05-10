-- =============================================
-- Migration: 008_extend_lora_models
-- Description: Add training dataset and quality assessment fields to lora_models
-- Date: 2026-05-11
-- 
-- This migration extends the lora_models table with:
-- 1. dataset_id - Link to training dataset used
-- 2. quality_score - Overall quality assessment score
-- 3. quality_report - Detailed quality assessment report (JSON)
-- 4. recommended_checkpoint_id - Link to best checkpoint
--
-- These fields connect LoRA models to their training data and
-- quality assessment results.
-- =============================================

-- Add new columns to lora_models table
ALTER TABLE lora_models ADD COLUMN dataset_id INTEGER REFERENCES training_datasets(id);
ALTER TABLE lora_models ADD COLUMN quality_score FLOAT;
ALTER TABLE lora_models ADD COLUMN quality_report JSON;
ALTER TABLE lora_models ADD COLUMN recommended_checkpoint_id INTEGER REFERENCES training_checkpoints(id);

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_lora_dataset ON lora_models(dataset_id);
CREATE INDEX IF NOT EXISTS idx_lora_quality_score ON lora_models(quality_score);
CREATE INDEX IF NOT EXISTS idx_lora_checkpoint ON lora_models(recommended_checkpoint_id);

-- =============================================
-- Comments and Documentation
-- =============================================

-- New columns added to lora_models:
-- dataset_id: Foreign key to training_datasets (which dataset was used for training)
-- quality_score: Overall quality score from assessment (0-100)
-- quality_report: JSON with detailed assessment results including:
--   - consistency_score: IP consistency score
--   - image_quality: Image quality score
--   - style_match: Style matching score
--   - diversity: Diversity score
--   - overfitting_detected: Boolean
--   - underfitting_detected: Boolean
--   - recommendations: List of improvement suggestions
-- recommended_checkpoint_id: Foreign key to training_checkpoints (best checkpoint to use)

-- Usage examples:
-- 
-- 1. Get all LoRA models trained from a specific dataset:
--    SELECT * FROM lora_models WHERE dataset_id = 1;
--
-- 2. Get high-quality LoRA models:
--    SELECT * FROM lora_models WHERE quality_score >= 85;
--
-- 3. Get LoRA model with its dataset info:
--    SELECT l.*, d.name as dataset_name 
--    FROM lora_models l 
--    LEFT JOIN training_datasets d ON l.dataset_id = d.id 
--    WHERE l.id = 1;
--
-- 4. Get quality report for a LoRA model:
--    SELECT quality_report FROM lora_models WHERE id = 1;
