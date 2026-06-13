"""
Generation Dispatcher

Core dispatch layer that routes generation requests to appropriate adapters
based on model capabilities. Implements the ComfyUI-style pluggable architecture
where the dispatcher acts as the central routing node.
"""
from typing import Dict, List, Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.adapters.base import BaseGenerationAdapter
from app.services.adapters.protocol import (
    GenerationRequest,
    GenerationResponse,
    GenerationCapability,
)
from app.services.adapters.text_adapter import TextGenerationAdapter
from app.services.adapters.image_adapter import ImageGenerationAdapter
from app.services.adapters.video_adapter import VideoGenerationAdapter
from app.models.llm_model import LLMConfig
from app.models.llm_provider import LLMProvider, LLMModel
from app.utils.logger import logger
from app.config.database import get_db_session_standalone


class GenerationDispatcher:
    """
    Central dispatch layer for generation requests.
    
    Architecture:
    1. Receive unified GenerationRequest
    2. Resolve channel (llm_configs) to get provider + model info
    3. Look up model capabilities from llm_models
    4. Select appropriate adapter based on generation_type + capabilities
    5. Dispatch to adapter for execution
    6. Return normalized GenerationResponse
    """

    def __init__(self):
        """Initialize dispatcher with registered adapters."""
        self._adapters: Dict[str, BaseGenerationAdapter] = {}
        self._capability_map: Dict[str, BaseGenerationAdapter] = {}

        # Register built-in adapters
        self._register_adapter(TextGenerationAdapter())
        self._register_adapter(ImageGenerationAdapter())
        self._register_adapter(VideoGenerationAdapter())

    def _register_adapter(self, adapter: BaseGenerationAdapter) -> None:
        """Register an adapter and map its capabilities."""
        adapter_name = adapter.__class__.__name__
        self._adapters[adapter_name] = adapter
        for capability in adapter.get_supported_capabilities():
            self._capability_map[capability] = adapter
        logger.info(f"Registered generation adapter: {adapter_name} (capabilities: {adapter.get_supported_capabilities()})")

    async def dispatch(self, request: GenerationRequest) -> GenerationResponse:
        """
        Dispatch a generation request to the appropriate adapter.
        
        Steps:
        1. Resolve channel from llm_configs
        2. Get model capabilities from llm_models
        3. Find matching adapter
        4. Execute generation
        5. Return normalized response
        """
        try:
            # Step 1: Resolve channel
            channel_info = await self._resolve_channel(request.channel_id)
            if not channel_info:
                return GenerationResponse(
                    status="failed",
                    output_type=request.generation_type,
                    error=f"Channel {request.channel_id} not found or inactive",
                )

            channel, provider, model = channel_info

            # Step 2: Get capabilities
            capabilities = model.capabilities if model else None
            if not capabilities:
                # Fallback: infer capabilities from generation_type
                capabilities = GenerationCapability.get_required_capabilities(request.generation_type)
                logger.warning(
                    f"No capabilities found for channel {request.channel_id}, "
                    f"inferring from generation_type: {capabilities}"
                )

            # Step 3: Find matching adapter
            adapter = self._find_adapter(request.generation_type, capabilities)
            if not adapter:
                return GenerationResponse(
                    status="failed",
                    output_type=request.generation_type,
                    error=f"No adapter found for generation_type={request.generation_type} "
                          f"with capabilities={capabilities}",
                )

            logger.info(
                f"Dispatching {request.generation_type} generation to {adapter.__class__.__name__} "
                f"via channel {request.channel_id} ({channel.name})"
            )

            # Enrich request with provider/model info so adapter can route to cloud API
            request.provider = channel.provider
            request.model_name = channel.model_name

            # Step 4: Execute generation
            response = await adapter.generate(request)

            # Step 5: Enrich metadata with channel info
            if response.metadata is None:
                response.metadata = {}
            response.metadata.update({
                "channel_name": channel.name,
                "provider": channel.provider,
                "model_name": channel.model_name,
                "capabilities": capabilities,
            })

            return response

        except Exception as e:
            logger.error(f"Dispatch failed for channel {request.channel_id}: {e}")
            return GenerationResponse(
                status="failed",
                output_type=request.generation_type,
                error=str(e),
            )

    async def _resolve_channel(
        self, channel_id: int
    ) -> Optional[tuple]:
        """
        Resolve a channel ID to its config, provider, and model info.
        
        Returns:
            Tuple of (LLMConfig, LLMProvider, LLMModel) or None
        """
        async with get_db_session_standalone() as db:
            try:
                # Get channel config
                result = await db.execute(
                    select(LLMConfig).where(
                        LLMConfig.id == channel_id,
                        LLMConfig.is_active == True,
                    )
                )
                channel = result.scalar_one_or_none()
                if not channel:
                    return None

                # Get provider
                provider_result = await db.execute(
                    select(LLMProvider).where(LLMProvider.code == channel.provider)
                )
                provider = provider_result.scalar_one_or_none()

                # Get model capabilities
                model = None
                if provider:
                    model_result = await db.execute(
                        select(LLMModel).where(
                            LLMModel.provider_id == provider.id,
                            LLMModel.code == channel.model_name,
                            LLMModel.is_active == True,
                        )
                    )
                    model = model_result.scalar_one_or_none()

                return (channel, provider, model)

            except Exception as e:
                logger.error(f"Failed to resolve channel {channel_id}: {e}")
                return None
        return None

    def _find_adapter(
        self, 
        generation_type: str, 
        capabilities: List[str],
    ) -> Optional[BaseGenerationAdapter]:
        """
        Find the appropriate adapter for a generation type and capabilities.
        
        Priority: match by capability first, then by generation_type fallback.
        """
        # Try to match by capability
        required = GenerationCapability.get_required_capabilities(generation_type)
        for cap in required:
            if cap in self._capability_map:
                return self._capability_map[cap]

        # Fallback: try direct capability match from model's capabilities
        for cap in capabilities:
            if cap in self._capability_map:
                return self._capability_map[cap]

        return None

    async def get_channels_by_capability(
        self, 
        capability: str,
    ) -> List[Dict]:
        """
        Get all active channels that support a given capability.
        
        Used by the frontend to populate model selectors filtered by tag.
        """
        channels = []
        async with get_db_session_standalone() as db:
            try:
                # Get all active channels
                result = await db.execute(
                    select(LLMConfig).where(LLMConfig.is_active == True)
                )
                active_channels = result.scalars().all()

                for channel in active_channels:
                    # Look up model capabilities
                    provider_result = await db.execute(
                        select(LLMProvider).where(LLMProvider.code == channel.provider)
                    )
                    provider = provider_result.scalar_one_or_none()

                    model_capabilities = None
                    if provider:
                        model_result = await db.execute(
                            select(LLMModel).where(
                                LLMModel.provider_id == provider.id,
                                LLMModel.code == channel.model_name,
                            )
                        )
                        model = model_result.scalar_one_or_none()
                        if model and model.capabilities:
                            model_capabilities = model.capabilities

                    # Check if channel supports the requested capability
                    if model_capabilities and capability in model_capabilities:
                        channels.append({
                            "id": channel.id,
                            "name": channel.name,
                            "provider": channel.provider,
                            "model_name": channel.model_name,
                            "model_type": channel.model_type,
                            "capabilities": model_capabilities,
                            "provider_icon": provider.icon_class if provider else "fas fa-brain",
                            "provider_icon_url": provider.icon_url if provider else None,
                        })
                    elif not model_capabilities and capability in [GenerationCapability.TEXT_GENERATION, GenerationCapability.CHAT]:
                        # Fallback: if no capabilities set, assume text generation for cloud/local LLMs
                        channels.append({
                            "id": channel.id,
                            "name": channel.name,
                            "provider": channel.provider,
                            "model_name": channel.model_name,
                            "model_type": channel.model_type,
                            "capabilities": [GenerationCapability.TEXT_GENERATION, GenerationCapability.CHAT],
                            "provider_icon": provider.icon_class if provider else "fas fa-brain",
                            "provider_icon_url": provider.icon_url if provider else None,
                        })

            except Exception as e:
                logger.error(f"Failed to get channels by capability {capability}: {e}")

        return channels


# Global dispatcher instance
generation_dispatcher = GenerationDispatcher()
