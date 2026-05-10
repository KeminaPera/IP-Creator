-- =============================================
-- Migration: 007_create_test_images_and_checkpoints
-- Description: Create test images and training checkpoints tables
-- Date: 2026-05-11
-- 
-- This migration creates tables for:
-- 1. test_images - Generated test images for quality assessment
-- 2. training_checkpoints - Training checkpoint files during LoRA training
--
-- These tables support the quality assessment workflow by storing
-- test images and training checkpoints for evaluation.
-- =============================================

-- =============================================
-- 1. Test Images Table
-- =============================================
CREATE TABLE IF NOT EXISTS test_images (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- LoRA Model Association
    lora_model_id INTEGER NOT NULL REFERENCES lora_models(id) ON DELETE CASCADE,
    
    -- File Information
    file_path VARCHAR(500) NOT NULL,
    
    -- Generation Parameters
    prompt TEXT,
    negative_prompt TEXT,
    
    -- Quality Metrics
    quality_score FLOAT,
    consistency_score FLOAT,
    
    -- Test Category
    test_category VARCHAR(50),
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for test_images
CREATE INDEX IF NOT EXISTS idx_test_images_lora ON test_images(lora_model_id);
CREATE INDEX IF NOT EXISTS idx_test_images_category ON test_images(test_category);
CREATE INDEX IF NOT EXISTS idx_test_images_quality ON test_images(quality_score);
CREATE INDEX IF NOT EXISTS idx_test_images_consistency ON test_images(consistency_score);

-- =============================================
-- 2. Training Checkpoints Table
-- =============================================
CREATE TABLE IF NOT EXISTS training_checkpoints (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- LoRA Model Association
    lora_model_id INTEGER NOT NULL REFERENCES lora_models(id) ON DELETE CASCADE,
    
    -- Checkpoint File
    file_path VARCHAR(500) NOT NULL,
    
    -- Training Progress
    epoch INTEGER NOT NULL,
    step INTEGER,
    loss FLOAT,
    
    -- Recommendation
    is_recommended BOOLEAN DEFAULT 0,
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for training_checkpoints
CREATE INDEX IF NOT EXISTS idx_checkpoints_lora ON training_checkpoints(lora_model_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_epoch ON training_checkpoints(epoch);
CREATE INDEX IF NOT EXISTS idx_checkpoints_recommended ON training_checkpoints(is_recommended);
CREATE INDEX IF NOT EXISTS idx_checkpoints_lora_epoch ON training_checkpoints(lora_model_id, epoch);

-- =============================================
-- Comments and Documentation
-- =============================================

-- test_images table comments:
-- id: Primary Key
-- lora_model_id: Foreign key to lora_models (which LoRA this test is for)
-- file_path: Path to the test image file
-- prompt: Text prompt used for generation
-- negative_prompt: Negative prompt used
-- quality_score: Image quality score (0-100)
-- consistency_score: How consistent with IP reference images (0-100)
-- test_category: What aspect this test evaluates (front_view/side_view/expression/action)
-- created_at: Generation timestamp

-- training_checkpoints table comments:
-- id: Primary Key
-- lora_model_id: Foreign key to lora_models
-- file_path: Path to the checkpoint .safetensors file
-- epoch: Epoch number when saved
-- step: Step number within epoch
-- loss: Training loss value at this point
-- is_recommended: Whether this checkpoint is recommended as the best
-- created_at: Checkpoint save timestamp
