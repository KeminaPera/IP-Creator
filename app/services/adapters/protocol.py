"""
Unified Generation Protocol

Defines the standard input/output protocol for all generation adapters.
Inspired by ComfyUI's node-based architecture with unified interfaces.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    """
    Unified generation request across all model types.
    
    The adapter layer translates this into model-specific parameters.
    """
    prompt: str = Field(..., description="Generation prompt")
    generation_type: str = Field(
        ..., description="Type of generation: 'text', 'image', or 'video'"
    )
    channel_id: int = Field(
        ..., description="Channel ID from llm_configs (configured model with API key)"
    )
    provider: Optional[str] = Field(
        None, description="Provider code (e.g., 'zhipu', 'openai', 'dashscope') - set by dispatcher"
    )
    model_name: Optional[str] = Field(
        None, description="Model identifier (e.g., 'cogview-3-plus', 'dall-e-3') - set by dispatcher"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific parameters (resolution, steps, etc.)"
    )
    ip_asset_id: Optional[int] = Field(
        None, description="Associated IP asset ID for file storage"
    )
    ip_name: Optional[str] = Field(
        None, description="IP character name for prompt enhancement"
    )
    style: Optional[str] = Field(
        None, description="Style preset (healing, comedy, etc.)"
    )


class GenerationResponse(BaseModel):
    """
    Unified generation response across all model types.
    
    Adapters normalize model-specific outputs into this standard format.
    """
    status: str = Field(..., description="'success' or 'failed'")
    output_url: Optional[str] = Field(None, description="URL to generated output file")
    output_path: Optional[str] = Field(None, description="Local path to generated output file")
    output_type: str = Field(..., description="'text', 'image', or 'video'")
    content: Optional[str] = Field(None, description="Text content (for text generation)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Generation metadata (parameters, model info, etc.)"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


# Capability constants for tag-based filtering
class GenerationCapability:
    """Capability tags used in llm_models.capabilities JSON field."""
    TEXT_GENERATION = "text_generation"
    CHAT = "chat"
    CODE = "code"
    VISION = "vision"
    REASONING = "reasoning"
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_GENERATION = "image_generation"
    TEXT_TO_VIDEO = "text_to_video"
    VIDEO_GENERATION = "video_generation"
    TEXT_TO_AUDIO = "text_to_audio"
    AUDIO_GENERATION = "audio_generation"
    MULTI_MODAL = "multi_modal"

    # Mapping: generation_type -> required capabilities (any match)
    CAPABILITY_MAP = {
        "text": [TEXT_GENERATION, CHAT],
        "image": [TEXT_TO_IMAGE, IMAGE_GENERATION],
        "video": [TEXT_TO_VIDEO, VIDEO_GENERATION],
    }

    @classmethod
    def get_required_capabilities(cls, generation_type: str) -> List[str]:
        """Get the capability tags that qualify a model for a generation type."""
        return cls.CAPABILITY_MAP.get(generation_type, [])

    @classmethod
    def model_supports_type(cls, model_capabilities: Optional[List[str]], generation_type: str) -> bool:
        """Check if a model's capabilities support a given generation type."""
        if not model_capabilities:
            return False
        required = cls.get_required_capabilities(generation_type)
        return any(cap in model_capabilities for cap in required)
