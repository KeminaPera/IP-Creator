-- =============================================
-- Migration: 009_create_ip_feature_library
-- Description: Create IP feature library tables for managing outfits, expressions, poses, etc.
-- Date: 2026-05-10
-- 
-- This migration creates tables for:
-- 1. ip_multi_views - Standard multi-view images (front/side/back)
-- 2. ip_feature_library - Feature library (outfits, expressions, poses, etc.)
-- 3. ip_feature_images - Images for each feature
--
-- These tables support the LoRA training workflow by managing
-- diverse character features that can be combined for training.
-- =============================================

-- =============================================
-- 1. IP Multi-Views Table
-- =============================================
CREATE TABLE IF NOT EXISTS ip_multi_views (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- IP Asset Association
    ip_asset_id INTEGER NOT NULL,
    
    -- View Type
    view_type VARCHAR(20) NOT NULL,
    -- Values: front, side, back, three_quarter_front, three_quarter_back
    
    -- Image Information
    image_path VARCHAR(500) NOT NULL,
    width INTEGER,
    height INTEGER,
    
    -- Source
    source VARCHAR(20) NOT NULL,
    -- Values: generated (AI generated), uploaded (user uploaded)
    
    -- Generation Parameters (if AI generated)
    generation_params JSON,
    -- Example: {"prompt": "...", "seed": 123, "model": "sd1.5"}
    
    -- Status
    is_primary BOOLEAN DEFAULT FALSE,
    quality_score FLOAT,
    -- Quality score 0-100
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key
    FOREIGN KEY (ip_asset_id) REFERENCES ip_assets(id) ON DELETE CASCADE
);

-- Indexes for ip_multi_views
CREATE INDEX IF NOT EXISTS idx_multi_views_ip ON ip_multi_views(ip_asset_id);
CREATE INDEX IF NOT EXISTS idx_multi_views_type ON ip_multi_views(view_type);
CREATE INDEX IF NOT EXISTS idx_multi_views_primary ON ip_multi_views(is_primary);

-- =============================================
-- 2. IP Feature Library Table
-- =============================================
CREATE TABLE IF NOT EXISTS ip_feature_library (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- IP Asset Association
    ip_asset_id INTEGER NOT NULL,
    
    -- Feature Type
    feature_type VARCHAR(50) NOT NULL,
    -- Values: outfit, expression, pose, background, accessory, etc.
    -- Extensible: new types can be added without schema changes
    
    -- Feature Identification
    feature_name VARCHAR(100) NOT NULL,
    -- Example: "casual_wear", "kimono", "happy", "standing"
    
    -- Display Name
    display_name VARCHAR(100),
    -- Example: "常服", "和服", "开心", "站立"
    
    -- Description
    description TEXT,
    
    -- Trigger Phrase for Generation
    trigger_phrase VARCHAR(200),
    -- Example: "wearing casual clothes", "happy expression", "standing pose"
    
    -- Reference Images (JSON array for quick access)
    reference_images JSON,
    -- Example: [{"angle": "front", "path": "/path.jpg"}, ...]
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key
    FOREIGN KEY (ip_asset_id) REFERENCES ip_assets(id) ON DELETE CASCADE,
    
    -- Unique Constraint
    UNIQUE(ip_asset_id, feature_type, feature_name)
);

-- Indexes for ip_feature_library
CREATE INDEX IF NOT EXISTS idx_feature_library_ip ON ip_feature_library(ip_asset_id);
CREATE INDEX IF NOT EXISTS idx_feature_library_type ON ip_feature_library(feature_type);
CREATE INDEX IF NOT EXISTS idx_feature_library_active ON ip_feature_library(is_active);
CREATE INDEX IF NOT EXISTS idx_feature_library_name ON ip_feature_library(feature_name);

-- =============================================
-- 3. IP Feature Images Table
-- =============================================
CREATE TABLE IF NOT EXISTS ip_feature_images (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Feature Association
    feature_id INTEGER NOT NULL,
    
    -- Angle
    angle VARCHAR(20) NOT NULL,
    -- Values: front, side, back
    
    -- Image Path
    image_path VARCHAR(500) NOT NULL,
    width INTEGER,
    height INTEGER,
    
    -- Source
    source VARCHAR(20) NOT NULL,
    -- Values: generated, uploaded
    
    -- Generation Parameters
    generation_params JSON,
    
    -- Quality
    quality_score FLOAT,
    -- Quality score 0-100
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Key
    FOREIGN KEY (feature_id) REFERENCES ip_feature_library(id) ON DELETE CASCADE
);

-- Indexes for ip_feature_images
CREATE INDEX IF NOT EXISTS idx_feature_images_feature ON ip_feature_images(feature_id);
CREATE INDEX IF NOT EXISTS idx_feature_images_angle ON ip_feature_images(angle);

-- =============================================
-- Sample Data (Optional - for testing)
-- =============================================

-- Example: Insert sample feature types configuration
-- Note: This is just for reference, actual config is in app/config/feature_types.py

/*
Feature Type Configuration Reference:

outfit (服装):
  - trigger_template: "wearing {feature_name}"
  - required: true
  - min_images: 3 (front/side/back)
  
expression (表情):
  - trigger_template: "{feature_name} expression"
  - required: true
  - min_images: 1 (front only)
  
pose (动作):
  - trigger_template: "{feature_name} pose"
  - required: true
  - min_images: 3 (front/side/back)

Future extensible types:
  - accessory (配饰): glasses, hat, jewelry
  - hairstyle (发型): long_hair, short_hair, ponytail
  - background (背景): forest, city, indoor
  - prop (道具): weapon, tool, pet
  - weather (天气): sunny, rainy, snowy
  - lighting (光照): daylight, moonlight, neon
*/

-- =============================================
-- Migration Complete
-- =============================================

-- Verify tables created
SELECT 'ip_multi_views' as table_name, COUNT(*) as record_count FROM ip_multi_views
UNION ALL
SELECT 'ip_feature_library', COUNT(*) FROM ip_feature_library
UNION ALL
SELECT 'ip_feature_images', COUNT(*) FROM ip_feature_images;
