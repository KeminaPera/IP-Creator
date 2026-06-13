"""
CloudVideo Node

Generates videos via cloud API (Zhipu CogVideoX, Dashscope Wan2.1).
Wraps generation_dispatcher.dispatch() for cloud video generation within FlowPipe.
"""
import uuid
from datetime import datetime
from pathlib import Path

from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


@register_node
class CloudVideoNode(BaseNode):
    NAME = "CloudVideo"
    DISPLAY_NAME = "Cloud Video Generation"
    CATEGORY = "Generate/Cloud"
    FUNCTION = "generate"
    OUTPUT_NODE = True
    DESCRIPTION = "Generate videos via cloud API (Zhipu CogVideoX / Dashscope)"

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
                "image_path": ("STRING", {
                    "default": "",
                    "label": "Starting Image Path (for image-to-video)",
                }),
                "duration_seconds": ("INT", {
                    "default": 5,
                    "min": 1,
                    "max": 30,
                    "label": "Duration (seconds)",
                }),
                "fps": ("INT", {
                    "default": 24,
                    "min": 4,
                    "max": 60,
                    "label": "FPS",
                }),
                "width": ("INT", {
                    "default": 512,
                    "min": 256,
                    "max": 2048,
                    "step": 64,
                    "label": "Width",
                }),
                "height": ("INT", {
                    "default": 512,
                    "min": 256,
                    "max": 2048,
                    "step": 64,
                    "label": "Height",
                }),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {"video_path": PortType.STRING, "video_url": PortType.STRING}

    async def generate(self, prompt: str, channel_id: int,
                       image_path: str = "", duration_seconds: int = 5,
                       fps: int = 24, width: int = 512, height: int = 512):
        from app.core.generation_dispatcher import generation_dispatcher
        from app.services.adapters.protocol import GenerationRequest

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Auto-select channel if not specified
        if channel_id <= 0:
            channel_id = await self._auto_select_channel("video")
            if channel_id <= 0:
                raise ValueError("No active video-generation channel found. Please configure one in LLM Management or specify channel_id.")

        gen_request = GenerationRequest(
            prompt=prompt,
            generation_type="video",
            channel_id=channel_id,
            parameters={
                "image_path": image_path or None,
                "duration_seconds": duration_seconds,
                "fps": fps,
                "width": width,
                "height": height,
                "steps": 50,
                "cfg_scale": 7.0,
            },
        )

        logger.info(f"[CloudVideo] channel={channel_id}, prompt={prompt[:60]}...")

        response = await generation_dispatcher.dispatch(gen_request)

        if response.status == "failed":
            raise RuntimeError(response.error or "Cloud video generation failed")

        output_path = response.output_path or ""
        output_url = response.output_url or ""

        # If adapter returned a URL but no local path, download it
        if output_url and not output_path:
            output_path = await self._download_video(output_url)

        logger.info(f"[CloudVideo] Generated: {output_path}")
        return {"video_path": output_path, "video_url": output_url}

    async def _download_video(self, url: str) -> str:
        """Download video from URL to local storage."""
        try:
            import httpx
            project_root = Path(__file__).resolve().parent.parent.parent
            out_dir = project_root / "data" / "videos"
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"cloud_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.mp4"
            filepath = out_dir / filename

            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                filepath.write_bytes(resp.content)

            return str(filepath)
        except Exception as e:
            logger.warning(f"[CloudVideo] Failed to download video: {e}")
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
            logger.warning(f"[CloudVideo] Auto-select channel failed: {e}")
            return 0
