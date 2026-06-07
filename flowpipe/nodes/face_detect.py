"""
FaceDetect Node

Detects faces in a reference image using insightface FaceAnalysis.
Extracts face bounding box and face objects for downstream nodes.
"""
from pathlib import Path

import numpy as np
from PIL import Image

from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


@register_node
class FaceDetectNode(BaseNode):
    NAME = "FaceDetect"
    DISPLAY_NAME = "Face Detector"
    CATEGORY = "Preprocess/Detect"
    FUNCTION = "detect"
    DESCRIPTION = "Detect faces in a reference image using insightface"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": (PortType.IMAGE, {"runtime": True}),
                "model_name": ("STRING", {
                    "default": "buffalo_l",
                    "options": ["buffalo_l", "buffalo_m", "buffalo_s"],
                    "label": "Detection Model",
                }),
                "det_size": ("STRING", {
                    "default": "640",
                    "options": ["320", "480", "640", "800"],
                    "label": "Detection Size",
                }),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {
            "faces": PortType.FACES,
            "bbox": PortType.BBOX,
            "face_image": PortType.IMAGE,
        }

    def detect(self, image, model_name: str, det_size: str):
        from insightface.app import FaceAnalysis

        # Accept both PIL Image and file path string
        if isinstance(image, str):
            logger.info(f"[FaceDetect] Loading image from path: {image}")
            image = Image.open(image).convert("RGB")

        project_root = Path(__file__).resolve().parent.parent.parent
        insightface_root = str(project_root / "data" / "models" / "insightface")

        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        import torch
        ctx_id = 0 if torch.cuda.is_available() else -1
        det = int(det_size)

        logger.info(f"[FaceDetect] Initializing {model_name} (det_size={det})")
        face_app = FaceAnalysis(
            name=model_name,
            root=insightface_root,
            providers=providers,
        )
        face_app.prepare(ctx_id=ctx_id, det_size=(det, det))

        img_np = np.array(image)
        img_np = img_np[:, :, ::-1]  # RGB -> BGR
        faces = face_app.get(img_np)

        if len(faces) == 0:
            logger.warning("[FaceDetect] No faces detected")
            return {"faces": None, "bbox": None, "face_image": image}

        primary_face = faces[0]
        bbox = tuple(primary_face.bbox)
        logger.info(
            f"[FaceDetect] Detected {len(faces)} face(s), "
            f"primary bbox={bbox}, confidence={primary_face.det_score:.3f}"
        )

        return {"faces": faces, "bbox": bbox, "face_image": image}
