-- =============================================
-- Migration: 006_create_training_datasets
-- Description: Create training dataset management tables
-- Date: 2026-05-11
-- 
-- This migration creates tables for:
-- 1. training_datasets - Dataset metadata and quality metrics
-- 2. dataset_images - Individual images in datasets with annotations
--
-- These tables support the LoRA training workflow by managing
-- training datasets with quality checks and version control.
-- =============================================

-- =============================================
-- 1. Training Datasets Table
-- =============================================
CREATE TABLE IF NOT EXISTS training_datasets (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- IP Asset Association
    ip_asset_id INTEGER NOT NULL REFERENCES ip_assets(id),
    
    -- Dataset Identification
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Dataset Statistics
    image_count INTEGER DEFAULT 0,
    augmented_count INTEGER DEFAULT 0,
    total_size_mb FLOAT DEFAULT 0.0,
    
    -- Quality Metrics
    quality_score FLOAT,
    angle_coverage JSON,
    diversity_score FLOAT,
    consistency_score FLOAT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    validation_report JSON,
    
    -- Version Management
    version INTEGER DEFAULT 1,
    parent_version_id INTEGER REFERENCES training_datasets(id),
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for training_datasets
CREATE INDEX IF NOT EXISTS idx_datasets_ip_asset ON training_datasets(ip_asset_id);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON training_datasets(status);
CREATE INDEX IF NOT EXISTS idx_datasets_quality ON training_datasets(quality_score);
CREATE INDEX IF NOT EXISTS idx_datasets_version ON training_datasets(version);
CREATE INDEX IF NOT EXISTS idx_datasets_ip_version ON training_datasets(ip_asset_id, version);

-- =============================================
-- 2. Dataset Images Table
-- =============================================
CREATE TABLE IF NOT EXISTS dataset_images (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Dataset Association
    dataset_id INTEGER NOT NULL REFERENCES training_datasets(id) ON DELETE CASCADE,
    
    -- File Information
    file_path VARCHAR(500) NOT NULL,
    width INTEGER,
    height INTEGER,
    file_size_kb INTEGER,
    
    -- Annotations
    angle VARCHAR(20),
    expression VARCHAR(50),
    pose VARCHAR(50),
    background VARCHAR(50),
    
    -- Quality Assessment
    quality_score FLOAT,
    
    -- Augmentation Tracking
    is_augmented BOOLEAN DEFAULT 0,
    parent_image_id INTEGER REFERENCES dataset_images(id),
    
    -- Usage Status
    is_selected BOOLEAN DEFAULT 1,
    rejection_reason VARCHAR(200),
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for dataset_images
CREATE INDEX IF NOT EXISTS idx_images_dataset ON dataset_images(dataset_id);
CREATE INDEX IF NOT EXISTS idx_images_angle ON dataset_images(angle);
CREATE INDEX IF NOT EXISTS idx_images_quality ON dataset_images(quality_score);
CREATE INDEX IF NOT EXISTS idx_images_selected ON dataset_images(is_selected);
CREATE INDEX IF NOT EXISTS idx_images_augmented ON dataset_images(is_augmented);
CREATE INDEX IF NOT EXISTS idx_images_parent ON dataset_images(parent_image_id);

-- =============================================
-- Comments and Documentation
-- =============================================

-- training_datasets table comments:
-- id: Primary Key
-- ip_asset_id: Foreign key to ip_assets (which IP this dataset is for)
-- name: Dataset name (e.g., "My Character Dataset v1")
-- description: Dataset description
-- image_count: Number of original images uploaded
-- augmented_count: Total images after augmentation
-- total_size_mb: Total size of all images in MB
-- quality_score: Overall quality score calculated from validation
-- angle_coverage: JSON object with count per angle
-- diversity_score: How diverse the images are (0-100)
-- consistency_score: How consistent the images are (0-100)
-- status: Dataset status workflow: pending -> validating -> ready -> training -> archived
-- validation_report: JSON with detailed validation results
-- version: Version number (increments with each major change)
-- parent_version_id: Links to previous version for tracking changes
-- created_at: Creation timestamp
-- updated_at: Update timestamp

-- dataset_images table comments:
-- id: Primary Key
-- dataset_id: Foreign key to training_datasets
-- file_path: Path to the image file
-- width: Image width in pixels
-- height: Image height in pixels
-- file_size_kb: File size in KB
-- angle: Image angle (front/side/back/full_body/half_body)
-- expression: Character expression
-- pose: Character pose
-- background: Background type
-- quality_score: Individual image quality score (0-100)
-- is_augmented: Whether this image was generated via augmentation
-- parent_image_id: If augmented, links to original image
-- is_selected: Whether this image will be used for training
-- rejection_reason: Why image was rejected (if not selected)
-- created_at: Upload timestamp
