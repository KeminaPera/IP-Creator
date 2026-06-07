"""
ImagePreproc Node

Preprocesses reference images: face-aware crop, center crop, resize.
"""
from PIL import Image

from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


@register_node
class ImagePreprocNode(BaseNode):
    NAME = "ImagePreproc"
    DISPLAY_NAME = "Image Preprocessor"
    CATEGORY = "Preprocess/Image"
    FUNCTION = "preprocess"
    DESCRIPTION = "Preprocess reference images with face-aware or center crop"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": (PortType.IMAGE, {"runtime": True}),
                "target_size": ("INT", {
                    "default": 512,
                    "min": 256,
                    "max": 2048,
                    "step": 64,
                    "label": "Target Size",
                }),
                "mode": ("STRING", {
                    "default": "face_aware_crop",
                    "options": ["face_aware_crop", "center_crop", "resize"],
                    "label": "Crop Mode",
                }),
                "padding_factor": ("FLOAT", {
                    "default": 1.5,
                    "min": 1.0,
                    "max": 3.0,
                    "step": 0.1,
                    "label": "Face Padding Factor",
                }),
            },
            "optional": {
                "bbox": (PortType.BBOX, {}),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {"images": PortType.IMAGE_LIST}

    def preprocess(self, image, target_size: int,
                   mode: str, padding_factor: float, bbox=None):
        # Accept both PIL Image and file path string
        if isinstance(image, str):
            logger.info(f"[ImagePreproc] Loading image from path: {image}")
            image = Image.open(image).convert("RGB")

        image = image.convert("RGB")

        if mode == "face_aware_crop" and bbox is not None:
            result = self._crop_face_region(image, bbox, target_size, padding_factor)
            logger.info(f"[ImagePreproc] Face-aware crop: bbox={bbox}, size={image.size}")
        elif mode == "center_crop":
            result = self._center_crop(image, target_size)
        else:
            result = image.resize((target_size, target_size), Image.Resampling.LANCZOS)

        return {"images": [result]}

    @staticmethod
    def _crop_face_region(image, face_bbox, target_size, padding_factor):
        x1, y1, x2, y2 = face_bbox
        w, h = image.size
        face_cx = (x1 + x2) / 2
        face_cy = (y1 + y2) / 2
        face_side = max(x2 - x1, y2 - y1)
        expanded = face_side * padding_factor
        half = expanded / 2

        crop_x1 = max(0, int(face_cx - half))
        crop_y1 = max(0, int(face_cy - half))
        crop_x2 = min(w, int(face_cx + half))
        crop_y2 = min(h, int(face_cy + half))

        crop_w = crop_x2 - crop_x1
        crop_h = crop_y2 - crop_y1
        crop_side = max(crop_w, crop_h)
        crop_cx = (crop_x1 + crop_x2) / 2
        crop_cy = (crop_y1 + crop_y2) / 2
        crop_x1 = max(0, int(crop_cx - crop_side / 2))
        crop_y1 = max(0, int(crop_cy - crop_side / 2))
        crop_x2 = crop_x1 + crop_side
        crop_y2 = crop_y1 + crop_side

        if crop_x2 > w:
            crop_x2 = w
            crop_x1 = max(0, crop_x2 - crop_side)
        if crop_y2 > h:
            crop_y2 = h
            crop_y1 = max(0, crop_y2 - crop_side)

        cropped = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        return cropped.resize((target_size, target_size), Image.Resampling.LANCZOS)

    @staticmethod
    def _center_crop(image, target_size):
        w, h = image.size
        scale = target_size / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_size) // 2
        top = (new_h - target_size) // 2
        if new_w < target_size or new_h < target_size:
            padded = Image.new("RGB", (target_size, target_size), (255, 255, 255))
            padded.paste(image, ((target_size - new_w) // 2, (target_size - new_h) // 2))
            return padded
        return image.crop((left, top, left + target_size, top + target_size))
