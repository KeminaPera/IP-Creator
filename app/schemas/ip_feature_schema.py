"""
IP Feature Library Schemas

Pydantic schemas for IP feature library management including
multi-views, feature library (outfits, expressions, poses), and feature images.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================
# Multi-View Schemas
# ============================================

class MultiViewBase(BaseModel):
    """Base schema for multi-view."""
    view_type: str = Field(
        ..., 
        description="View type: front, side, back, three_quarter_front, three_quarter_back"
    )
    image_path: str = Field(..., description="Path to the image file")
    width: Optional[int] = Field(None, description="Image width in pixels")
    height: Optional[int] = Field(None, description="Image height in pixels")
    source: str = Field(..., description="Source: generated or uploaded")
    is_primary: bool = Field(False, description="Whether this is the primary view")
    quality_score: Optional[float] = Field(None, ge=0, le=100, description="Quality score 0-100")

    @validator('view_type')
    def validate_view_type(cls, v):
        allowed = ['front', 'side', 'back', 'three_quarter_front', 'three_quarter_back']
        if v not in allowed:
            raise ValueError(f'view_type must be one of: {", ".join(allowed)}')
        return v

    @validator('source')
    def validate_source(cls, v):
        if v not in ['generated', 'uploaded', 'workflow']:
            raise ValueError('source must be "generated", "uploaded", or "workflow"')
        return v


class MultiViewCreate(MultiViewBase):
    """Schema for creating a multi-view."""
    generation_params: Optional[Dict[str, Any]] = Field(None, description="Generation parameters if AI generated")


class MultiViewResponse(MultiViewBase):
    """Schema for multi-view response."""
    id: int
    ip_asset_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MultiViewListResponse(BaseModel):
    """Schema for multi-view list response (data only, wrapper handled by success_response())."""
    data: List[MultiViewResponse]


# ============================================
# Feature Library Schemas
# ============================================

class FeatureBase(BaseModel):
    """Base schema for feature."""
    feature_type: str = Field(..., description="Feature type: outfit, expression, pose, etc.")
    feature_name: str = Field(..., min_length=1, max_length=100, description="Feature name in English")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name in user's language")
    description: Optional[str] = Field(None, description="Feature description")
    trigger_phrase: Optional[str] = Field(None, max_length=200, description="Trigger phrase for generation")
    is_active: bool = Field(True, description="Whether this feature is active")


class FeatureCreate(FeatureBase):
    """Schema for creating a feature."""
    reference_images: Optional[List[Dict[str, str]]] = Field(
        None, 
        description="Reference images: [{angle: 'front', path: '/path.jpg'}, ...]"
    )


class FeatureUpdate(BaseModel):
    """Schema for updating a feature."""
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    trigger_phrase: Optional[str] = Field(None, max_length=200)
    reference_images: Optional[List[Dict[str, str]]] = None
    is_active: Optional[bool] = None


class FeatureImageBase(BaseModel):
    """Base schema for feature image."""
    angle: str = Field(..., description="View angle: front, side, back")
    image_path: str = Field(..., description="Path to the image file")
    width: Optional[int] = Field(None, description="Image width")
    height: Optional[int] = Field(None, description="Image height")
    source: str = Field(..., description="Source: generated or uploaded")
    quality_score: Optional[float] = Field(None, ge=0, le=100, description="Quality score")

    @validator('angle')
    def validate_angle(cls, v):
        allowed = ['front', 'side', 'back']
        if v not in allowed:
            raise ValueError(f'angle must be one of: {", ".join(allowed)}')
        return v

    @validator('source')
    def validate_source(cls, v):
        if v not in ['generated', 'uploaded', 'workflow']:
            raise ValueError('source must be "generated", "uploaded", or "workflow"')
        return v


class FeatureImageCreate(FeatureImageBase):
    """Schema for creating a feature image."""
    generation_params: Optional[Dict[str, Any]] = Field(None, description="Generation parameters")


class FeatureImageResponse(FeatureImageBase):
    """Schema for feature image response."""
    id: int
    feature_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FeatureResponse(FeatureBase):
    """Schema for feature response."""
    id: int
    ip_asset_id: int
    reference_images: Optional[List[Dict[str, str]]] = None
    images: List[FeatureImageResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FeatureListResponse(BaseModel):
    """Schema for feature list response (data only, wrapper handled by success_response())."""
    data: List[FeatureResponse]


# ============================================
# Feature Type Configuration Schemas
# ============================================

class FeatureTypeConfig(BaseModel):
    """Schema for feature type configuration."""
    type: str
    display_name: str
    display_name_en: str
    icon: str
    trigger_template: str
    required: bool
    min_images: int
    caption_position: int
    description: str
    description_en: str


class FeatureTypeListResponse(BaseModel):
    """Schema for feature type list response (data only, wrapper handled by success_response())."""
    data: List[FeatureTypeConfig]


# ============================================
# Batch Operation Schemas
# ============================================

class BatchFeatureCreate(BaseModel):
    """Schema for batch creating features."""
    features: List[FeatureCreate]


class FeatureImageUpload(BaseModel):
    """Schema for feature image upload response (data only, wrapper handled by success_response())."""
    data: FeatureImageResponse


class FeatureValidationResult(BaseModel):
    """Schema for feature validation result."""
    feature_id: int
    feature_name: str
    is_valid: bool
    missing_angles: List[str] = []
    has_all_required_images: bool
    message: Optional[str] = None
