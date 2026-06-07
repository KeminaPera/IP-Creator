"""
LoRALoader Node

Loads LoRA weights onto a pipeline. Optional node in the workflow.
"""
from pathlib import Path

from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


@register_node
class LoRALoaderNode(BaseNode):
    NAME = "LoRALoader"
    DISPLAY_NAME = "LoRA Loader"
    CATEGORY = "Model/LoRA"
    FUNCTION = "load_lora"
    DESCRIPTION = "Load LoRA weights onto the pipeline"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pipe": (PortType.MODEL, {}),
                "weight": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.5,
                    "step": 0.05,
                    "label": "LoRA Weight",
                }),
            },
            "optional": {
                "lora_path": ("STRING", {
                    "default": "",
                    "label": "LoRA Model Path",
                }),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {"pipe": PortType.MODEL}

    def load_lora(self, pipe, weight, lora_path=""):
        if not lora_path or not Path(lora_path).exists():
            logger.info("[LoRALoader] No LoRA path provided or file not found, skipping")
            return {"pipe": pipe}

        try:
            pipe.load_lora_weights(lora_path)
            pipe.fuse_lora(lora_scale=weight)
            logger.info(f"[LoRALoader] Loaded LoRA: {lora_path} (weight={weight})")
        except Exception as e:
            logger.warning(f"[LoRALoader] Failed to load LoRA: {e}")

        return {"pipe": pipe}
