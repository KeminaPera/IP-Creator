"""
ImageSave Node

Saves a generated image to disk and returns the file path.
"""
import io
import uuid
from datetime import datetime
from pathlib import Path

from PIL import Image

from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


@register_node
class ImageSaveNode(BaseNode):
    NAME = "ImageSave"
    DISPLAY_NAME = "Image Save"
    CATEGORY = "Output/Save"
    FUNCTION = "save"
    OUTPUT_NODE = True
    DESCRIPTION = "Save generated image to disk"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": (PortType.IMAGE, {}),
                "format": ("STRING", {
                    "default": "PNG",
                    "options": ["PNG", "JPEG"],
                    "label": "Format",
                }),
            },
            "optional": {
                "output_dir": ("STRING", {
                    "default": "",
                    "label": "Output Directory (empty = data/videos/images)",
                }),
                "ip_asset_id": ("INT", {
                    "default": 0,
                    "label": "IP Asset ID (auto-sets output_dir to ip_N/)",
                }),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {"path": PortType.STRING, "image_bytes": PortType.ANY}

    def save(self, image: Image.Image, format: str, output_dir: str = "", ip_asset_id: int = 0):
        if not output_dir:
            project_root = Path(__file__).resolve().parent.parent.parent
            if ip_asset_id and ip_asset_id > 0:
                output_dir = str(project_root / "data" / "videos" / "images" / f"ip_{ip_asset_id}")
            else:
                output_dir = str(project_root / "data" / "videos" / "images")

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        filename = f"flowpipe_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{format.lower()}"
        filepath = out_path / filename

        image.save(str(filepath), format=format, quality=95)
        logger.info(f"[ImageSave] Saved: {filepath}")

        # Also produce bytes for API response
        buf = io.BytesIO()
        image.save(buf, format=format, quality=95)
        buf.seek(0)

        return {"path": str(filepath), "image_bytes": buf.getvalue()}
