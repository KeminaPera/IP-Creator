"""
SDModelLoader Node

Loads a Stable Diffusion base pipeline with configurable model,
scheduler, and precision. Replaces the hardcoded SD 1.5 loading
in ip_adapter_service._ensure_pipeline().
"""
import os
from pathlib import Path

import torch
from PIL import Image

from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


# Scheduler name -> diffusers class name mapping
_SCHEDULER_MAP = {
    "dpmsolver++_karras": ("DPMSolverMultistepScheduler", {"use_karras_sigmas": True, "algorithm_type": "dpmsolver++"}),
    "dpmsolver++": ("DPMSolverMultistepScheduler", {"algorithm_type": "dpmsolver++"}),
    "euler_a": ("EulerAncestralDiscreteScheduler", {}),
    "ddim": ("DDIMScheduler", {}),
    "dpm2_karras": ("DPMSolverSinglestepScheduler", {"use_karras_sigmas": True}),
    "heun": ("HeunDiscreteScheduler", {}),
}


@register_node
class SDModelLoaderNode(BaseNode):
    NAME = "SDModelLoader"
    DISPLAY_NAME = "SD Model Loader"
    CATEGORY = "Model/Loader"
    FUNCTION = "load_model"
    DESCRIPTION = "Load a Stable Diffusion base pipeline with configurable model and scheduler"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_id": ("STRING", {
                    "default": "runwayml/stable-diffusion-v1-5",
                    "options": [
                        "runwayml/stable-diffusion-v1-5",
                        "stabilityai/stable-diffusion-xl-base-1.0",
                    ],
                    "label": "Base Model",
                }),
                "scheduler": ("STRING", {
                    "default": "dpmsolver++_karras",
                    "options": list(_SCHEDULER_MAP.keys()),
                    "label": "Scheduler",
                }),
                "dtype": ("STRING", {
                    "default": "float16",
                    "options": ["float16", "float32"],
                    "label": "Precision",
                }),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {"pipe": PortType.MODEL, "scheduler_name": PortType.STRING}

    def load_model(self, model_id: str, scheduler: str, dtype: str):
        from diffusers import StableDiffusionPipeline

        from app.config.settings import settings

        torch_dtype = torch.float16 if dtype == "float16" else torch.float32

        # Determine device
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Resolve local model path
        _cache_root = Path(settings.HF_HUB_CACHE_PATH).resolve()
        model_slug = "models--" + model_id.replace("/", "--")
        _sd_model_dir = _cache_root / model_slug / "snapshots"
        _local_model_path = model_id
        if _sd_model_dir.exists():
            _snapshots = list(_sd_model_dir.iterdir())
            if _snapshots:
                _local_model_path = str(_snapshots[0])
                logger.info(f"[SDModelLoader] Using local model: {_local_model_path}")

        logger.info(f"[SDModelLoader] Loading pipeline: {model_id} (dtype={dtype})")
        pipe = StableDiffusionPipeline.from_pretrained(
            _local_model_path,
            torch_dtype=torch_dtype,
            safety_checker=None,
            requires_safety_checker=False,
            local_files_only=True,
        )

        # Replace scheduler
        sched_key = scheduler if scheduler in _SCHEDULER_MAP else "dpmsolver++_karras"
        sched_cls_name, sched_kwargs = _SCHEDULER_MAP[sched_key]
        try:
            import diffusers
            sched_cls = getattr(diffusers, sched_cls_name)
            pipe.scheduler = sched_cls.from_config(pipe.scheduler.config, **sched_kwargs)
            logger.info(f"[SDModelLoader] Scheduler: {sched_cls_name} ({sched_kwargs})")
        except Exception as e:
            logger.warning(f"[SDModelLoader] Failed to set scheduler: {e}, using default")

        pipe = pipe.to(device)

        return {"pipe": pipe, "scheduler_name": sched_key}
