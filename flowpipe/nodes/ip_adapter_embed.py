"""
IPAdapterEmbed Node

Loads IP-Adapter weights onto a pipeline and extracts embeddings
from reference images. Supports original, faceid, and faceid-plus modes.
"""
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import CLIPImageProcessor

from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.config.settings import settings
from app.utils.logger import logger


# Mode -> weight config mapping
_MODE_CONFIGS = {
    "original": {
        "repo": "h94/IP-Adapter",
        "subfolder": "models",
        "weight_name": "ip-adapter_sd15.bin",
        "cache_dir_name": "models--h94--IP-Adapter",
        "image_encoder_folder": "image_encoder",
        "scale_range": (0.5, 0.8),
    },
    "faceid": {
        "repo": "h94/IP-Adapter-FaceID",
        "subfolder": None,
        "weight_name": "ip-adapter-faceid_sd15.bin",
        "cache_dir_name": "models--h94--IP-Adapter-FaceID",
        "image_encoder_folder": None,
        "scale_range": (0.8, 1.0),
    },
    "faceid-plus": {
        "repo": "h94/IP-Adapter-FaceID",
        "subfolder": None,
        "weight_name": "ip-adapter-faceid-plus_sd15.bin",
        "cache_dir_name": "models--h94--IP-Adapter-FaceID",
        "image_encoder_folder": "ip-adapter-faceid-plus_sd15/image_encoder",
        "scale_range": (0.7, 1.0),
    },
}


@register_node
class IPAdapterEmbedNode(BaseNode):
    NAME = "IPAdapterEmbed"
    DISPLAY_NAME = "IP-Adapter Embeddings"
    CATEGORY = "Embedding/Extract"
    FUNCTION = "extract"
    DESCRIPTION = "Load IP-Adapter weights and extract embeddings from reference images"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pipe": (PortType.MODEL, {}),
                "images": (PortType.IMAGE_LIST, {}),
                "mode": ("STRING", {
                    "default": "faceid-plus",
                    "options": ["original", "faceid", "faceid-plus"],
                    "label": "IP-Adapter Mode",
                }),
                "ip_adapter_scale": ("FLOAT", {
                    "default": 0.93,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "label": "IP-Adapter Scale",
                }),
            },
            "optional": {
                "faces": (PortType.FACES, {}),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {
            "pipe": PortType.MODEL,
            "embeddings": PortType.EMBEDDINGS,
        }

    def extract(self, pipe, images, mode, ip_adapter_scale, faces=None):
        config = _MODE_CONFIGS.get(mode, _MODE_CONFIGS["faceid-plus"])

        # Load IP-Adapter weights
        self._load_ip_adapter(pipe, config)

        # Clamp scale to valid range
        lo, hi = config["scale_range"]
        scale = max(lo, min(hi, ip_adapter_scale))
        if scale != ip_adapter_scale:
            logger.info(f"[IPAdapterEmbed] Scale clamped {ip_adapter_scale:.2f} -> {scale:.2f}")

        pipe.set_ip_adapter_scale(scale)

        # Extract embeddings based on mode
        if mode == "original":
            embeddings = self._extract_original(pipe, images)
        else:
            embeddings = self._extract_faceid(pipe, images, faces, mode)

        return {"pipe": pipe, "embeddings": embeddings}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_ip_adapter(pipe, config):
        cache_root = Path(settings.HF_HUB_CACHE_PATH).resolve()
        ip_dir = cache_root / config["cache_dir_name"] / "snapshots"
        if not ip_dir.exists():
            raise FileNotFoundError(f"IP-Adapter cache not found: {ip_dir}")

        snapshots = list(ip_dir.iterdir())
        if not snapshots:
            raise FileNotFoundError(f"No snapshots in {ip_dir}")

        snapshot_path = snapshots[0]
        logger.info(f"[IPAdapterEmbed] Loading from {snapshot_path}")

        pipe.load_ip_adapter(
            str(snapshot_path),
            subfolder=config["subfolder"],
            weight_name=config["weight_name"],
            image_encoder_folder=config["image_encoder_folder"],
        )

    @staticmethod
    def _extract_original(pipe, images):
        return {
            "ip_adapter_image": images[0] if len(images) == 1 else images,
        }

    @staticmethod
    def _extract_faceid(pipe, images, faces, mode):
        if not faces:
            # Try detection on preprocessed image
            from insightface.app import FaceAnalysis
            project_root = Path(__file__).resolve().parent.parent.parent
            insightface_root = str(project_root / "data" / "models" / "insightface")
            face_app = FaceAnalysis(name="buffalo_l", root=insightface_root,
                                    providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
            ctx_id = 0 if torch.cuda.is_available() else -1
            face_app.prepare(ctx_id=ctx_id, det_size=(640, 640))

            img_np = np.array(images[0])[:, :, ::-1]
            faces = face_app.get(img_np)
            if len(faces) == 0:
                raise RuntimeError("No face detected in reference image")

        face = faces[0]
        device = next(pipe.unet.parameters()).device
        dtype = pipe.unet.dtype

        # Build FaceID embedding: (2, 1, 512)
        positive = torch.from_numpy(face.normed_embedding).unsqueeze(0).unsqueeze(0)
        positive = positive.to(device, dtype=dtype)
        negative = torch.zeros_like(positive)
        faceid_embed = torch.cat([negative, positive], dim=0)

        result = {"ip_adapter_image_embeds": [faceid_embed]}

        # FaceID-Plus: add CLIP hidden states
        if mode == "faceid-plus":
            clip_embeds = IPAdapterEmbedNode._extract_clip_embeds(pipe, images[0])
            proj = pipe.unet.encoder_hid_proj.image_projection_layers[0]
            proj.clip_embeds = clip_embeds.repeat(faceid_embed.shape[0], 1, 1, 1)

        return result

    @staticmethod
    def _extract_clip_embeds(pipe, pil_image):
        image_encoder = pipe.image_encoder
        crop_size = image_encoder.config.image_size
        processor = CLIPImageProcessor(
            do_resize=True, size={"shortest_edge": crop_size},
            do_center_crop=True, crop_size=crop_size, do_normalize=True,
        )
        device = next(image_encoder.parameters()).device
        pixel_values = processor(images=pil_image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(device, dtype=image_encoder.dtype)

        with torch.no_grad():
            hidden = image_encoder(pixel_values).last_hidden_state

        return hidden.unsqueeze(1).to(device, dtype=pipe.unet.dtype)
