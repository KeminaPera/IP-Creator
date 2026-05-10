"""
Video Generation Adapter

Translates unified generation requests into video generation calls.
Supports:
- Cloud APIs: Zhipu CogVideoX, Dashscope Wan2.1
- Local: DiffusionService (CogVideoX I2V)
"""
from typing import List, Optional

from app.services.adapters.base import BaseGenerationAdapter
from app.services.adapters.protocol import GenerationRequest, GenerationResponse, GenerationCapability
from app.services.cloud_gen_service import cloud_gen_service
from app.services.diffusion_service import diffusion_service
from app.services.storage_service import storage_service
from app.config.database import async_session_factory
from app.models.llm_model import LLMConfig
from app.security.crypto import encryption_service
from sqlalchemy import select
from app.utils.logger import logger

# Cloud providers that support video generation via API
CLOUD_VIDEO_PROVIDERS = {"zhipu", "dashscope"}


class VideoGenerationAdapter(BaseGenerationAdapter):
    """
    Adapter for video generation.
    
    Routes to the appropriate backend based on provider:
    - Cloud providers (zhipu, dashscope) → cloud API
    - Local providers (ollama, local) → DiffusionService
    """

    def get_supported_capabilities(self) -> List[str]:
        return [GenerationCapability.TEXT_TO_VIDEO, GenerationCapability.VIDEO_GENERATION]

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate video using cloud API or local DiffusionService.
        
        Routes based on request.provider:
        - zhipu/dashscope → cloud_gen_service
        - local/ollama → DiffusionService
        """
        try:
            provider = request.provider
            model_name = request.model_name
            
            if provider in CLOUD_VIDEO_PROVIDERS:
                return await self._generate_cloud(request, provider, model_name)
            else:
                return await self._generate_local(request)

        except Exception as e:
            logger.error(f"Video generation failed via adapter: {e}")
            return GenerationResponse(
                status="failed",
                output_type="video",
                error=str(e),
            )

    async def _generate_cloud(
        self, request: GenerationRequest, provider: str, model_name: str
    ) -> GenerationResponse:
        """Generate video via cloud API."""
        params = request.parameters
        
        # Get API credentials from channel config
        channel = await self._get_channel_config(request.channel_id)
        if not channel:
            return GenerationResponse(
                status="failed",
                output_type="video",
                error=f"Channel {request.channel_id} not found",
            )
        
        api_key = encryption_service.decrypt(channel.api_key_encrypted) if channel.api_key_encrypted else None
        if not api_key:
            return GenerationResponse(
                status="failed",
                output_type="video",
                error=f"No API key configured for channel {request.channel_id}",
            )
        
        api_endpoint = channel.api_endpoint
        image_path = params.get("image_path")
        
        logger.info(
            f"Cloud video generation: provider={provider}, model={model_name}, "
            f"prompt={request.prompt[:50]}..."
        )
        
        result = await cloud_gen_service.generate_video(
            provider=provider,
            model_name=model_name,
            prompt=request.prompt,
            api_key=api_key,
            api_endpoint=api_endpoint,
            image_url=image_path,  # Cloud APIs use URL, not local path
        )
        
        if result["status"] == "failed":
            return GenerationResponse(
                status="failed",
                output_type="video",
                error=result.get("error", "Cloud video generation failed"),
            )
        
        # Handle video result - could be bytes or URL
        video_bytes = result.get("video_bytes")
        video_url = result.get("video_url")
        
        if video_bytes:
            file_path, file_url = await storage_service.save_generated_video(
                video_data=video_bytes,
                ip_asset_id=request.ip_asset_id or 0,
            )
            output_url = file_url
            output_path = file_path
        elif video_url:
            # Download from URL and save
            import httpx
            async with httpx.AsyncClient(timeout=300.0) as client:
                vid_response = await client.get(video_url)
                vid_response.raise_for_status()
                video_bytes = vid_response.content
            
            file_path, file_url = await storage_service.save_generated_video(
                video_data=video_bytes,
                ip_asset_id=request.ip_asset_id or 0,
            )
            output_url = file_url
            output_path = file_path
        else:
            return GenerationResponse(
                status="failed",
                output_type="video",
                error="No video data in cloud API response",
            )
        
        logger.info(f"Cloud video generated successfully: {output_url}")
        
        return GenerationResponse(
            status="success",
            output_type="video",
            output_url=output_url,
            output_path=output_path,
            metadata={
                "channel_id": request.channel_id,
                "provider": provider,
                "model_name": model_name,
                "prompt": request.prompt,
            },
        )

    async def _generate_local(self, request: GenerationRequest) -> GenerationResponse:
        """Generate video using local DiffusionService."""
        from pathlib import Path
        
        params = request.parameters
        
        # Extract standard parameters with defaults
        image_path = params.get("image_path")
        duration_seconds = params.get("duration_seconds", 5)
        fps = params.get("fps", 24)
        width = params.get("width", 512)
        height = params.get("height", 512)
        steps = params.get("steps", 50)
        cfg_scale = params.get("cfg_scale", 7.0)

        logger.info(f"Local video generation via DiffusionService: {request.prompt[:50]}...")
        logger.info(f"Channel: {request.channel_id}, Duration: {duration_seconds}s, FPS: {fps}")

        # Validate: video generation typically requires a starting image
        if not image_path or not Path(image_path).exists():
            return GenerationResponse(
                status="failed",
                output_type="video",
                error="Starting image is required for video generation",
            )

        # Call diffusion service for video generation
        result = await diffusion_service.generate_image_to_video(
            image_path=image_path,
            prompt=request.prompt,
            duration_seconds=duration_seconds,
            fps=fps,
            width=width,
            height=height,
            steps=steps,
        )

        if result["status"] == "failed":
            return GenerationResponse(
                status="failed",
                output_type="video",
                error=result.get("error", "Video generation failed"),
            )

        # Save generated video
        video_bytes = result["video_bytes"]
        file_path, file_url = await storage_service.save_generated_video(
            video_data=video_bytes,
            ip_asset_id=request.ip_asset_id or 0,
        )

        return GenerationResponse(
            status="success",
            output_type="video",
            output_url=file_url,
            output_path=file_path,
            metadata={
                "channel_id": request.channel_id,
                "provider": request.provider,
                "parameters": result.get("parameters", {}),
                "prompt": request.prompt,
            },
        )

    async def _get_channel_config(self, channel_id: int) -> Optional[LLMConfig]:
        """Look up channel config from database."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(LLMConfig).where(LLMConfig.id == channel_id)
            )
            return result.scalar_one_or_none()
