"""
Image Generation Adapter

Translates unified generation requests into image generation calls.
Supports:
- Cloud APIs: Zhipu CogView, OpenAI DALL-E, Dashscope Wanx
- Local: DiffusionService (Stable Diffusion + LoRA + IP-Adapter)
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

# Cloud providers that support image generation via API
CLOUD_IMAGE_PROVIDERS = {"zhipu", "openai", "dashscope"}


class ImageGenerationAdapter(BaseGenerationAdapter):
    """
    Adapter for image generation.
    
    Routes to the appropriate backend based on provider:
    - Cloud providers (zhipu, openai, dashscope) → cloud API
    - Local providers (ollama, local) → DiffusionService
    """

    def get_supported_capabilities(self) -> List[str]:
        return [GenerationCapability.TEXT_TO_IMAGE, GenerationCapability.IMAGE_GENERATION]

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate image using cloud API or local DiffusionService.
        
        Routes based on request.provider:
        - zhipu/openai/dashscope → cloud_gen_service
        - local/ollama → DiffusionService
        """
        try:
            provider = request.provider
            model_name = request.model_name
            
            if provider in CLOUD_IMAGE_PROVIDERS:
                return await self._generate_cloud(request, provider, model_name)
            else:
                return await self._generate_local(request)

        except Exception as e:
            logger.error(f"Image generation failed via adapter: {e}")
            return GenerationResponse(
                status="failed",
                output_type="image",
                error=str(e),
            )

    async def _generate_cloud(
        self, request: GenerationRequest, provider: str, model_name: str
    ) -> GenerationResponse:
        """Generate image via cloud API."""
        params = request.parameters
        
        # Get API credentials from channel config
        channel = await self._get_channel_config(request.channel_id)
        if not channel:
            return GenerationResponse(
                status="failed",
                output_type="image",
                error=f"Channel {request.channel_id} not found",
            )
        
        api_key = encryption_service.decrypt(channel.api_key_encrypted) if channel.api_key_encrypted else None
        if not api_key:
            return GenerationResponse(
                status="failed",
                output_type="image",
                error=f"No API key configured for channel {request.channel_id}",
            )
        
        api_endpoint = channel.api_endpoint
        width = params.get("width", 1024)
        height = params.get("height", 1024)
        
        logger.info(
            f"Cloud image generation: provider={provider}, model={model_name}, "
            f"size={width}x{height}, prompt={request.prompt[:50]}..."
        )
        
        result = await cloud_gen_service.generate_image(
            provider=provider,
            model_name=model_name,
            prompt=request.prompt,
            api_key=api_key,
            api_endpoint=api_endpoint,
            width=width,
            height=height,
        )
        
        if result["status"] == "failed":
            return GenerationResponse(
                status="failed",
                output_type="image",
                error=result.get("error", "Cloud image generation failed"),
            )
        
        # Save generated image
        image_bytes = result["image_bytes"]
        file_path, file_url = await storage_service.save_generated_image(
            image_data=image_bytes,
            ip_asset_id=request.ip_asset_id or 0,
        )
        
        logger.info(f"Cloud image generated successfully: {file_url}")
        
        return GenerationResponse(
            status="success",
            output_type="image",
            output_url=file_url,
            output_path=file_path,
            metadata={
                "channel_id": request.channel_id,
                "provider": provider,
                "model_name": model_name,
                "parameters": {"width": width, "height": height},
                "prompt": request.prompt,
            },
        )

    async def _generate_local(self, request: GenerationRequest) -> GenerationResponse:
        """Generate image using local DiffusionService."""
        params = request.parameters
        
        # Extract standard parameters with defaults
        width = params.get("width", 512)
        height = params.get("height", 512)
        steps = params.get("steps", 30)
        cfg_scale = params.get("cfg_scale", 7.0)
        lora_path = params.get("lora_path")
        lora_weight = params.get("lora_weight", 0.7)
        use_ip_adapter = params.get("use_ip_adapter", False)
        ip_adapter_scale = params.get("ip_adapter_scale", 0.7)
        reference_images = params.get("reference_images")
        negative_prompt = params.get("negative_prompt", "")
        seed = params.get("seed")

        logger.info(f"Local image generation via DiffusionService: {request.prompt[:50]}...")
        logger.info(f"Channel: {request.channel_id}, LoRA: {lora_path}, IP-Adapter: {use_ip_adapter}")

        # Choose generation method based on parameters
        if use_ip_adapter and reference_images:
            if lora_path:
                result = await diffusion_service.generate_image_with_lora_and_ip(
                    prompt=request.prompt,
                    reference_images=reference_images,
                    lora_path=lora_path,
                    lora_weight=lora_weight,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    steps=steps,
                    cfg_scale=cfg_scale,
                    ip_adapter_scale=ip_adapter_scale,
                    seed=seed,
                )
            else:
                result = await diffusion_service.generate_image_with_ip_adapter(
                    prompt=request.prompt,
                    reference_images=reference_images,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    steps=steps,
                    cfg_scale=cfg_scale,
                    ip_adapter_scale=ip_adapter_scale,
                    seed=seed,
                )
        else:
            result = await diffusion_service.generate_image(
                prompt=request.prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg_scale=cfg_scale,
                seed=seed,
                lora_path=lora_path,
                lora_weight=lora_weight,
            )

        if result["status"] == "failed":
            return GenerationResponse(
                status="failed",
                output_type="image",
                error=result.get("error", "Image generation failed"),
            )

        # Save generated image
        image_bytes = result["image_bytes"]
        file_path, file_url = await storage_service.save_generated_image(
            image_data=image_bytes,
            ip_asset_id=request.ip_asset_id or 0,
        )

        return GenerationResponse(
            status="success",
            output_type="image",
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
