"""
DiffusionSampler Node

Runs the diffusion sampling process with the given pipeline,
embeddings, and prompt. This is the core image generation step.
"""
import torch
from PIL import Image

from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


@register_node
class DiffusionSamplerNode(BaseNode):
    NAME = "DiffusionSampler"
    DISPLAY_NAME = "Diffusion Sampler"
    CATEGORY = "Sampling/Generate"
    FUNCTION = "sample"
    DESCRIPTION = "Run diffusion sampling to generate an image"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pipe": (PortType.MODEL, {}),
                "embeddings": (PortType.EMBEDDINGS, {}),
                "prompt": (PortType.STRING, {}),
                "neg_prompt": (PortType.STRING, {}),
                "steps": ("INT", {
                    "default": 30,
                    "min": 10,
                    "max": 100,
                    "step": 1,
                    "label": "Sampling Steps",
                }),
                "cfg_scale": ("FLOAT", {
                    "default": 5.5,
                    "min": 1.0,
                    "max": 20.0,
                    "step": 0.5,
                    "label": "CFG Scale",
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
            "optional": {
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 2**32 - 1,
                    "label": "Seed (0 = random)",
                }),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {"image": PortType.IMAGE}

    def sample(self, pipe, embeddings, prompt, neg_prompt,
               steps, cfg_scale, width, height, seed=0):
        generator = None
        if seed and seed > 0:
            device = next(pipe.unet.parameters()).device
            generator = torch.Generator(device=device).manual_seed(int(seed))

        gen_kwargs = {
            "prompt": prompt,
            "negative_prompt": neg_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": cfg_scale,
            "generator": generator,
            "num_images_per_prompt": 1,
            **embeddings,
        }

        logger.info(
            f"[DiffusionSampler] Generating: {prompt[:50]}... "
            f"({width}x{height}, steps={steps}, cfg={cfg_scale})"
        )

        try:
            result = pipe(**gen_kwargs)
        finally:
            # Clean up clip_embeds from projection layer
            self._cleanup_clip_embeds(pipe)

        image = result.images[0]
        logger.info(f"[DiffusionSampler] Generated image: {image.size}")
        return {"image": image}

    @staticmethod
    def _cleanup_clip_embeds(pipe):
        try:
            proj = getattr(pipe.unet, "encoder_hid_proj", None)
            if proj is None:
                return
            layers = getattr(proj, "image_projection_layers", None)
            if layers is None:
                return
            for layer in layers:
                if hasattr(layer, "clip_embeds"):
                    layer.clip_embeds = None
        except Exception:
            pass
