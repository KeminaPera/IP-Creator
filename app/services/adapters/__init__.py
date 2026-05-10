"""
Generation Adapters

ComfyUI-style pluggable adapter architecture for model-agnostic generation.
Each adapter translates the unified generation protocol to model-specific API calls.
"""
from app.services.adapters.base import BaseGenerationAdapter
from app.services.adapters.protocol import GenerationRequest, GenerationResponse
from app.services.adapters.text_adapter import TextGenerationAdapter
from app.services.adapters.image_adapter import ImageGenerationAdapter
from app.services.adapters.video_adapter import VideoGenerationAdapter

__all__ = [
    "BaseGenerationAdapter",
    "GenerationRequest",
    "GenerationResponse",
    "TextGenerationAdapter",
    "ImageGenerationAdapter",
    "VideoGenerationAdapter",
]
