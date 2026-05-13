-- Migration 010: Add training_diagnosis column to quality_reports
-- Date: 2026-05-10
-- Purpose: Store overfitting/underfitting detection results

ALTER TABLE quality_reports
ADD COLUMN training_diagnosis JSON NULL COMMENT 'Overfitting/underfitting detection results';

-- Add index for querying by diagnosis status (if needed in future)
-- CREATE INDEX idx_quality_reports_diagnosis ON quality_reports ((training_diagnosis->>'$.overall_status'));
