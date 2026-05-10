"""
IP Asset Schemas

Pydantic schemas for IP character asset management including
image uploads, tag management, and LoRA associations.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ImageReference(BaseModel):
    """Schema for a single reference image with angle information."""
    angle: str = Field(..., description="Image angle: front, side, half_body, full_body, etc.")
    path: str = Field(..., description="File path to the image")


class IPAssetBase(BaseModel):
    """Base schema for IP asset."""
    name: str = Field(..., min_length=1, max_length=100, description="IP character name")
    category: Optional[str] = Field(None, max_length=50, description="Category")
    description: Optional[str] = Field(None, description="IP description")
    trigger_word: str = Field(..., min_length=1, max_length=100, description="Unique trigger word")
    style_template: Optional[str] = Field(None, max_length=50, description="Style template")


class IPAssetCreate(IPAssetBase):
    """Schema for creating a new IP asset."""
    reference_images: Optional[List[Any]] = Field([], description="Reference images (list of paths or objects)")
    positive_tags: Optional[List[str]] = Field(None, description="Positive style tags")
    negative_tags: Optional[List[str]] = Field(None, description="Negative tags to avoid")
    lora_model_id: Optional[int] = Field(None, description="Associated LoRA model ID")


class IPAssetUpdate(BaseModel):
    """Schema for updating an IP asset."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    reference_images: Optional[List[Any]] = None
    positive_tags: Optional[List[str]] = None
    negative_tags: Optional[List[str]] = None
    trigger_word: Optional[str] = Field(None, min_length=1, max_length=100)
    style_template: Optional[str] = Field(None, max_length=50)
    lora_model_id: Optional[int] = None


class IPAssetResponse(IPAssetBase):
    """Schema for IP asset response."""
    id: int
    reference_images: Optional[List[Any]] = []
    positive_tags: Optional[List[str]] = None
    negative_tags: Optional[List[str]] = None
    lora_model_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class IPAssetListResponse(BaseModel):
    """Schema for paginated IP asset list."""
    total: int = Field(..., description="Total count")
    items: List[IPAssetResponse] = Field(..., description="IP assets")


class StyleTemplatePreset(BaseModel):
    """Schema for style template presets."""
    name: str
    description: str
    positive_tags: List[str]
    negative_tags: List[str]
