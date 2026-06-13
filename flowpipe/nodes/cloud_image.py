"""
CloudImage Node

Generates images via cloud API (Zhipu CogView, OpenAI DALL-E, Dashscope Wanx).
Wraps generation_dispatcher.dispatch() for cloud image generation within FlowPipe.
"""
import uuid
from datetime import datetime
from pathlib import Path

from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


@register_node
class CloudImageNode(BaseNode):
    NAME = "CloudImage"
    DISPLAY_NAME = "Cloud Image Generation"
    CATEGORY = "Generate/Cloud"
    FUNCTION = "generate"
    OUTPUT_NODE = True
    DESCRIPTION = "Generate images via cloud API (Zhipu/DALL-E/Dashscope)"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "label": "Prompt",
                }),
                "channel_id": ("INT", {
                    "default": 0,
                    "label": "LLM Channel ID",
                }),
            },
            "optional": {
                "negative_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "label": "Negative Prompt",
                }),
                "width": ("INT", {
                    "default": 1024,
                    "min": 256,
                    "max": 2048,
                    "step": 64,
                    "label": "Width",
                }),
                "height": ("INT", {
                    "default": 1024,
                    "min": 256,
                    "max": 2048,
                    "step": 64,
                    "label": "Height",
                }),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {"path": PortType.STRING, "url": PortType.STRING}

    async def generate(self, prompt: str, channel_id: int,
                       negative_prompt: str = "", width: int = 1024,
                       height: int = 1024):
        from app.core.generation_dispatcher import generation_dispatcher
        from app.services.adapters.protocol import GenerationRequest

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Auto-select channel if not specified
        if channel_id <= 0:
            channel_id = await self._auto_select_channel("image")
            if channel_id <= 0:
                raise ValueError("No active image-generation channel found. Please configure one in LLM Management or specify channel_id.")

        gen_request = GenerationRequest(
            prompt=prompt,
            generation_type="image",
            channel_id=channel_id,
            parameters={
                "width": width,
                "height": height,
                "negative_prompt": negative_prompt,
                "steps": 30,
                "cfg_scale": 7.0,
            },
        )

        logger.info(f"[CloudImage] channel={channel_id}, prompt={prompt[:60]}...")

        response = await generation_dispatcher.dispatch(gen_request)

        if response.status == "failed":
            raise RuntimeError(response.error or "Cloud image generation failed")

        output_path = response.output_path or ""
        output_url = response.output_url or ""

        # If adapter returned a URL but no local path, download it
        if output_url and not output_path:
            output_path = await self._download_image(output_url)

        logger.info(f"[CloudImage] Generated: {output_path}")
        return {"path": output_path, "url": output_url}

    async def _download_image(self, url: str) -> str:
        """Download image from URL to local storage."""
        try:
            import httpx
            project_root = Path(__file__).resolve().parent.parent.parent
            out_dir = project_root / "data" / "videos" / "images"
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"cloud_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
            filepath = out_dir / filename

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                filepath.write_bytes(resp.content)

            return str(filepath)
        except Exception as e:
            logger.warning(f"[CloudImage] Failed to download image: {e}")
            return ""

    @staticmethod
    async def _auto_select_channel(gen_type: str) -> int:
        """Auto-select the first active channel that may support the given generation type."""
        try:
            from sqlalchemy import select
            from app.config.database import get_sync_session
            from app.models.llm_model import LLMConfig

            # Known providers that support image/video generation
            image_providers = {"zhipu", "dashscope", "openai"}
            video_providers = {"zhipu", "dashscope"}
            target_providers = video_providers if gen_type == "video" else image_providers

            with get_sync_session() as session:
                # First try: find active channel from known image/video providers
                stmt = select(LLMConfig).where(LLMConfig.is_active == True)
                configs = session.execute(stmt).scalars().all()
                for cfg in configs:
                    if cfg.provider in target_providers:
                        return cfg.id
                # Fallback: any active cloud channel
                for cfg in configs:
                    if cfg.model_type == "cloud":
                        return cfg.id
            return 0
        except Exception as e:
            logger.warning(f"[CloudImage] Auto-select channel failed: {e}")
            return 0
