"""  
LLM Configuration Schemas

Pydantic schemas for LLM model registration, configuration,
and health status tracking with validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from enum import Enum


class ModelType(str, Enum):
    """LLM model type enumeration."""
    LOCAL = "local"
    CLOUD = "cloud"


class LLMConfigBase(BaseModel):
    """Base schema for LLM configuration."""
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    model_type: ModelType = Field(..., description="Model type: local or cloud")
    provider: str = Field(..., min_length=1, max_length=50, description="Provider name")
    model_name: str = Field(..., min_length=1, max_length=100, description="Model identifier")
    description: Optional[str] = Field(None, description="Model description")


class LLMConfigCreate(LLMConfigBase):
    """Schema for creating a new LLM configuration."""
    api_endpoint: Optional[str] = Field(None, max_length=500, description="API endpoint for cloud models")
    api_key: Optional[str] = Field(None, description="API key (will be encrypted)")
    local_path: Optional[str] = Field(None, max_length=500, description="Local model path")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(2048, ge=1, le=32000, description="Max tokens to generate")
    timeout: int = Field(60, ge=1, le=300, description="Request timeout in seconds")
    context_window: int = Field(4096, ge=512, le=128000, description="Context window size")
    additional_params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")


class LLMConfigUpdate(BaseModel):
    """Schema for updating an existing LLM configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    api_endpoint: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, description="New API key (will be encrypted)")
    local_path: Optional[str] = Field(None, max_length=500)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)
    timeout: Optional[int] = Field(None, ge=1, le=300)
    context_window: Optional[int] = Field(None, ge=512, le=128000)
    additional_params: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class LLMConfigResponse(LLMConfigBase):
    """Schema for LLM configuration response (excludes sensitive data)."""
    id: int
    api_endpoint: Optional[str] = None
    api_key_masked: Optional[str] = Field(None, description="Masked API key for display")
    local_path: Optional[str] = None
    temperature: float
    max_tokens: int
    timeout: int
    context_window: int
    additional_params: Optional[Dict[str, Any]] = None
    is_active: bool
    is_default: bool
    health_status: str
    last_health_check: Optional[datetime] = None
    response_time_ms: Optional[float] = None
    success_rate: float
    created_at: datetime
    updated_at: datetime
    
    # Provider display fields (added dynamically in API)
    provider_name: Optional[str] = Field(None, description="Provider display name")
    provider_icon: Optional[str] = Field(None, description="Provider icon (Font Awesome class)")
    provider_icon_url: Optional[str] = Field(None, description="Provider icon image URL")
    
    # Capability tags (joined from llm_models)
    capabilities: Optional[List[str]] = Field(None, description="Model capability tags (e.g. text_generation, text_to_image)")
    
    class Config:
        from_attributes = True


class LLMHealthStatus(BaseModel):
    """Schema for LLM health check response."""
    model_id: int
    model_name: str
    health_status: str
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None


class LLMSwitchRequest(BaseModel):
    """Schema for switching the active LLM model."""
    model_id: int = Field(..., description="ID of the model to switch to")


# ========== Provider and Model Management Schemas ==========

class LLMProviderCreate(BaseModel):
    """Schema for creating a new LLM provider."""
    code: str = Field(..., min_length=1, max_length=50, description="Unique identifier")
    name_cn: str = Field(..., min_length=1, max_length=100, description="Chinese name")
    name_en: str = Field(..., min_length=1, max_length=100, description="English name")
    icon_class: Optional[str] = Field(None, max_length=100, description="Font Awesome icon class")
    icon_url: Optional[str] = Field(None, max_length=500, description="Icon image path")
    website: Optional[str] = Field(None, max_length=500, description="Official website")
    api_docs_url: Optional[str] = Field(None, max_length=500, description="API documentation URL")
    default_endpoint: Optional[str] = Field(None, max_length=500, description="Default API endpoint")
    requires_api_key: bool = Field(True, description="Whether API key is required")
    api_key_pattern: Optional[str] = Field(None, max_length=200, description="API key format regex")
    is_active: bool = Field(True, description="Whether provider is available")
    is_recommended: bool = Field(False, description="Whether provider is recommended")
    sort_order: int = Field(0, description="Display order")
    description_cn: Optional[str] = Field(None, description="Chinese description")
    description_en: Optional[str] = Field(None, description="English description")


class LLMProviderUpdate(BaseModel):
    """Schema for updating an LLM provider."""
    name_cn: Optional[str] = Field(None, min_length=1, max_length=100)
    name_en: Optional[str] = Field(None, min_length=1, max_length=100)
    icon_class: Optional[str] = Field(None, max_length=100)
    icon_url: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=500)
    api_docs_url: Optional[str] = Field(None, max_length=500)
    default_endpoint: Optional[str] = Field(None, max_length=500)
    requires_api_key: Optional[bool] = None
    api_key_pattern: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None
    is_recommended: Optional[bool] = None
    sort_order: Optional[int] = None
    description_cn: Optional[str] = None
    description_en: Optional[str] = None


class LLMProviderResponse(LLMProviderCreate):
    """Schema for LLM provider response."""
    id: int
    name: Optional[str] = Field(None, description="Display name (defaults to name_cn)")
    last_synced_at: Optional[datetime] = Field(default=None, description="Last successful sync timestamp")
    created_at: datetime
    updated_at: datetime
    
    model_config = {'from_attributes': True, 'populate_by_name': True}


class LLMModelCreate(BaseModel):
    """Schema for creating a new LLM model."""
    provider_id: int = Field(..., description="Associated provider ID")
    code: str = Field(..., min_length=1, max_length=100, description="Model unique identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Model display name")
    version: Optional[str] = Field(None, max_length=50, description="Version number")
    capabilities: Optional[List[str]] = Field(None, description='["text_generation", "vision", "code"]')
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum context length")
    max_output_tokens: Optional[int] = Field(None, ge=1, description="Maximum output length")
    supports_streaming: bool = Field(True, description="Supports streaming output")
    supports_function_calling: bool = Field(False, description="Supports function calling")
    supports_vision: bool = Field(False, description="Supports vision/image input")
    input_price_per_million: Optional[float] = Field(None, ge=0, description="Input price per million tokens")
    output_price_per_million: Optional[float] = Field(None, ge=0, description="Output price per million tokens")
    speed_rating: Optional[int] = Field(None, ge=1, le=5, description="Speed rating 1-5")
    quality_rating: Optional[int] = Field(None, ge=1, le=5, description="Quality rating 1-5")
    is_active: bool = Field(True, description="Whether model is available")
    is_recommended: bool = Field(False, description="Whether model is recommended")
    sort_order: int = Field(0, description="Display order")
    release_date: Optional[date] = Field(None, description="Release date")
    deprecated_date: Optional[date] = Field(None, description="Deprecation date")
    description: Optional[str] = Field(None, description="Model description")


class LLMModelUpdate(BaseModel):
    """Schema for updating an LLM model."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    version: Optional[str] = Field(None, max_length=50)
    capabilities: Optional[List[str]] = None
    max_tokens: Optional[int] = Field(None, ge=1)
    max_output_tokens: Optional[int] = Field(None, ge=1)
    supports_streaming: Optional[bool] = None
    supports_function_calling: Optional[bool] = None
    supports_vision: Optional[bool] = None
    input_price_per_million: Optional[float] = Field(None, ge=0)
    output_price_per_million: Optional[float] = Field(None, ge=0)
    speed_rating: Optional[int] = Field(None, ge=1, le=5)
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    is_active: Optional[bool] = None
    is_recommended: Optional[bool] = None
    sort_order: Optional[int] = None
    release_date: Optional[date] = None
    deprecated_date: Optional[date] = None
    description: Optional[str] = None


class LLMModelResponse(LLMModelCreate):
    """Schema for LLM model response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProviderWithModelsResponse(LLMProviderResponse):
    """Schema for provider with nested models."""
    models: List[LLMModelResponse] = []
