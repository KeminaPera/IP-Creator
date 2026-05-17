"""
Training Dataset Schemas

Pydantic schemas for training dataset management including
dataset CRUD operations, image management, and quality metrics.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================
# Dataset Image Schemas
# ============================================

class DatasetImageBase(BaseModel):
    """Base schema for dataset image."""
    file_path: str = Field(..., description="Path to the image file")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    file_size_kb: Optional[int] = Field(None, description="File size in KB")
    angle: Optional[str] = Field(None, max_length=20, description="front, side, back, full_body, half_body")
    expression: Optional[str] = Field(None, max_length=50, description="happy, sad, angry, surprised, neutral")
    pose: Optional[str] = Field(None, max_length=50, description="standing, sitting, running, jumping")
    background: Optional[str] = Field(None, max_length=50, description="simple, complex, outdoor, indoor")
    quality_score: Optional[float] = Field(None, ge=0, le=100, description="Image quality score (0-100)")


class DatasetImageCreate(DatasetImageBase):
    """Schema for creating a dataset image."""
    is_augmented: bool = Field(False, description="Whether this is an augmented image")
    parent_image_id: Optional[int] = Field(None, description="Original image if augmented")


class DatasetImageResponse(DatasetImageBase):
    """Schema for dataset image response."""
    id: int
    dataset_id: int
    is_augmented: bool
    parent_image_id: Optional[int] = None
    is_selected: bool
    rejection_reason: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# Training Dataset Schemas
# ============================================

class TrainingDatasetBase(BaseModel):
    """Base schema for training dataset."""
    name: str = Field(..., min_length=1, max_length=100, description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")


class TrainingDatasetCreate(TrainingDatasetBase):
    """Schema for creating a training dataset."""
    ip_asset_id: int = Field(..., description="Which IP this dataset is for")
    image_paths: Optional[List[str]] = Field(
        default=[],
        description="List of image resource paths (from ImageUploader)"
    )


class TrainingDatasetUpdate(BaseModel):
    """Schema for updating a training dataset."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[str] = Field(None, description="pending, validating, ready, training, archived")
    validation_report: Optional[Dict[str, Any]] = None


class TrainingDatasetResponse(TrainingDatasetBase):
    """Schema for training dataset response."""
    id: int
    ip_asset_id: int
    image_count: int
    augmented_count: int
    total_size_mb: float
    quality_score: Optional[float] = None
    angle_coverage: Optional[Dict[str, int]] = None
    diversity_score: Optional[float] = None
    consistency_score: Optional[float] = None
    status: str
    validation_report: Optional[Dict[str, Any]] = None
    version: int
    parent_version_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TrainingDatasetDetail(TrainingDatasetResponse):
    """Schema for training dataset with images."""
    images: List[DatasetImageResponse] = []


class TrainingDatasetListResponse(BaseModel):
    """Schema for paginated training dataset list."""
    total: int = Field(..., description="Total count")
    items: List[TrainingDatasetResponse] = Field(..., description="Training datasets")


# ============================================
# Dataset Validation Schemas
# ============================================

class DatasetValidationRequest(BaseModel):
    """Schema for requesting dataset validation."""
    check_quality: bool = Field(True, description="Check image quality")
    check_angles: bool = Field(True, description="Check angle coverage")
    check_consistency: bool = Field(False, description="Check IP consistency (requires CLIP)")


class DatasetValidationReport(BaseModel):
    """Schema for dataset validation report."""
    total_images: int
    selected_images: int
    rejected_images: int
    quality_score: float
    angle_coverage: Dict[str, int]
    diversity_score: float
    consistency_score: float
    health_score: float = 0.0  # Comprehensive health score (0-100)
    health_grade: str = "N/A"  # S/A/B/C/D/F
    issues: List[str] = []
    recommendations: List[str] = []


# ============================================
# Image Upload Schemas
# ============================================

class ImageUploadResponse(BaseModel):
    """Schema for image upload response."""
    image_id: int
    file_path: str
    width: int
    height: int
    file_size_kb: int
    quality_score: Optional[float] = None


class BatchImageUploadResponse(BaseModel):
    """Schema for batch image upload response."""
    total_uploaded: int
    successful: List[ImageUploadResponse] = []
    failed: List[Dict[str, Any]] = []


# ============================================
# Dataset Generation Schemas
# ============================================

class DatasetGenerationRequest(BaseModel):
    """Schema for generating dataset from IP features."""
    ip_asset_id: int = Field(..., description="IP asset ID")
    selected_features: Dict[str, List[int]] = Field(
        default_factory=dict,
        description="Selected feature IDs by type: {'outfit': [1,2], 'expression': [3,4,5]}"
    )
    dataset_name: Optional[str] = Field(None, max_length=100, description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")


class DatasetPreviewRequest(BaseModel):
    """Schema for previewing dataset combinations."""
    ip_asset_id: int = Field(..., description="IP asset ID")
    selected_features: Dict[str, List[int]] = Field(
        default_factory=dict,
        description="Selected feature IDs by type"
    )


class DatasetConversionRequest(BaseModel):
    """Schema for converting dataset to Kohya format."""
    output_dir: Optional[str] = Field(None, description="Output directory path")


class DatasetAugmentationRequest(BaseModel):
    """Schema for applying data augmentation."""
    augmentation_types: List[str] = Field(
        default=["flip", "rotation", "color_jitter"],
        description="Types of augmentation: flip, rotation, color_jitter, combined"
    )
    multiplier: int = Field(
        default=2, 
        ge=1, 
        le=10,
        description="Augmentation multiplier (1-10)"
    )
    create_version: bool = Field(
        default=True, 
        description="Whether to create new dataset version"
    )


class AugmentationValidationRequest(BaseModel):
    """Schema for validating augmentation safety."""
    image_id: int = Field(..., description="Image ID to validate")
    augmentation_type: str = Field(
        ..., 
        max_length=50,
        description="Augmentation type: flip, rotation, color_jitter, combined"
    )
