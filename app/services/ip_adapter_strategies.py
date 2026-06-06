"""
IP-Adapter Strategy Pattern

Encapsulates the differences between three IP-Adapter modes:
- Original:  h94/IP-Adapter (CLIP image features, compatible with LoRA)
- FaceID:    h94/IP-Adapter-FaceID (insightface 512-dim embeddings)
- FaceID-Plus: h94/IP-Adapter-FaceID (insightface + CLIP ViT-H/14)

Usage:
    strategy = IPAdapterStrategyRegistry.get("faceid")
    config = strategy.get_model_config()
    adapter_kwargs = strategy.prepare_embeddings(pipe, ctx)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image
from transformers import CLIPImageProcessor

from app.config.settings import settings
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ModelConfig:
    """IP-Adapter model loading configuration."""
    repo: str
    subfolder: Optional[str]
    weight_name: str
    cache_dir_name: str
    image_encoder_folder: Optional[str]
    default_scale_range: Tuple[float, float]


@dataclass
class GenerationContext:
    """
    Generation context: shared input parameters for all modes.

    Strategies read the fields they need; unused fields are ignored.
    `face_app` is a mutable reference that may be set by strategies (lazy
    loading) and must be written back to the service after strategy execution.
    """
    # Common generation parameters
    prompt: str
    negative_prompt: str
    width: int
    height: int
    steps: int
    cfg_scale: float
    seed: Optional[int]
    ip_adapter_scale: float

    # Pre-processed reference images (PIL Image list)
    ref_images: List[Image.Image]

    # Runtime environment
    device: str          # "cuda" / "mps" / "cpu"
    dtype: torch.dtype   # torch.float16 / torch.float32

    # Shared heavy dependency (lazy-loaded, reused across strategies)
    face_app: Any = None   # insightface.FaceAnalysis instance

    # Pre-detected faces (from original image, before preprocessing)
    # If set, strategies skip face detection and reuse these results
    detected_faces: Optional[list] = None


# ---------------------------------------------------------------------------
# Abstract strategy base class
# ---------------------------------------------------------------------------

class IPAdapterStrategy(ABC):
    """
    IP-Adapter strategy base class.

    Defines the interface that captures the differences between modes.
    Concrete strategies override the abstract methods.
    """

    name: str  # "original" / "faceid" / "faceid-plus"

    @abstractmethod
    def get_model_config(self) -> ModelConfig:
        """Return the model loading configuration for this mode."""

    @abstractmethod
    def check_dependencies(self, ctx: GenerationContext) -> Tuple[bool, str]:
        """
        Check whether all dependencies for this mode are satisfied.

        Returns:
            (ok, reason) — reason is empty when ok is True.
        """

    @abstractmethod
    def prepare_embeddings(
        self,
        pipe,
        ctx: GenerationContext,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract embeddings and return a dict to merge into gen_kwargs.

        Returns None to signal failure, which triggers fallback to Original.
        """

    def supports_lora(self) -> bool:
        """Whether this mode is compatible with LoRA joint generation."""
        return False

    def validate_scale(self, scale: float, config: ModelConfig) -> float:
        """Clamp scale to the recommended range for this mode."""
        low, high = config.default_scale_range
        if not (low <= scale <= high):
            logger.warning(
                f"[{self.name}] scale {scale:.2f} outside [{low},{high}], clamping"
            )
            return max(low, min(high, scale))
        return scale


# ---------------------------------------------------------------------------
# Original IP-Adapter strategy
# ---------------------------------------------------------------------------

class OriginalIPAdapterStrategy(IPAdapterStrategy):
    """Original IP-Adapter (h94/IP-Adapter, CLIP image features)."""

    name = "original"

    def get_model_config(self) -> ModelConfig:
        return ModelConfig(
            repo="h94/IP-Adapter",
            subfolder="models",
            weight_name="ip-adapter_sd15.bin",
            cache_dir_name="models--h94--IP-Adapter",
            image_encoder_folder="image_encoder",
            default_scale_range=(0.5, 0.8),
        )

    def check_dependencies(self, ctx: GenerationContext) -> Tuple[bool, str]:
        return (True, "")  # No extra dependencies

    def prepare_embeddings(
        self,
        pipe,
        ctx: GenerationContext,
    ) -> Optional[Dict[str, Any]]:
        imgs = ctx.ref_images
        return {
            "ip_adapter_image": imgs[0] if len(imgs) == 1 else imgs,
        }

    def supports_lora(self) -> bool:
        return True  # Original is compatible with LoRA


# ---------------------------------------------------------------------------
# FaceID (non-Plus) strategy
# ---------------------------------------------------------------------------

class FaceIDStrategy(IPAdapterStrategy):
    """
    IP-Adapter-FaceID (insightface 512-dim embeddings, no CLIP ViT-H/14).

    Uses insightface buffalo_l to extract face identity embeddings.
    The embedding tensor shape is (2, 1, 512) = [negative, positive] to
    satisfy diffusers' classifier_free_guidance requirement.
    """

    name = "faceid"

    def get_model_config(self) -> ModelConfig:
        return ModelConfig(
            repo="h94/IP-Adapter-FaceID",
            subfolder=None,
            weight_name="ip-adapter-faceid_sd15.bin",
            cache_dir_name="models--h94--IP-Adapter-FaceID",
            image_encoder_folder=None,
            default_scale_range=(0.8, 1.0),
        )

    # -- dependency check ---------------------------------------------------

    def check_dependencies(self, ctx: GenerationContext) -> Tuple[bool, str]:
        # 1. insightface package
        try:
            import insightface  # noqa: F401
        except ImportError:
            return (False, "insightface not installed (pip install insightface onnxruntime-gpu)")

        # 2. buffalo_l model directory
        insightface_root = self._insightface_root()
        buffalo_l_path = insightface_root / "models" / "buffalo_l"
        if not buffalo_l_path.exists():
            return (False, f"buffalo_l model not found at {buffalo_l_path}")

        return (True, "")

    # -- embedding extraction -----------------------------------------------

    def prepare_embeddings(
        self,
        pipe,
        ctx: GenerationContext,
    ) -> Optional[Dict[str, Any]]:
        face_app = self._ensure_face_app(ctx)

        # Use pre-detected faces (from original image) if available,
        # otherwise detect in the preprocessed 512×512 image
        if ctx.detected_faces:
            faces = ctx.detected_faces
            logger.info(f"[{self.name}] Using pre-detected faces from original image")
        else:
            faces = self._detect_faces(face_app, ctx.ref_images[0])

        if not faces:
            logger.warning("No face detected — FaceID embedding extraction failed")
            return None  # Triggers fallback to Original

        embed = self._build_faceid_embed(faces[0], pipe, ctx)
        return {"ip_adapter_image_embeds": [embed]}

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _insightface_root() -> Path:
        """Resolve the insightface model root directory."""
        # Project-local path: data/models/insightface
        project_root = Path(__file__).resolve().parent.parent.parent
        return project_root / "data" / "models" / "insightface"

    def _ensure_face_app(self, ctx: GenerationContext):
        """Lazy-load insightface FaceAnalysis, store in ctx for reuse."""
        if ctx.face_app is not None:
            return ctx.face_app

        from insightface.app import FaceAnalysis

        insightface_root = str(self._insightface_root())
        logger.info(f"Initializing insightface FaceAnalysis (root={insightface_root})")

        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        ctx_id = 0 if ctx.device == "cuda" else -1

        ctx.face_app = FaceAnalysis(
            name="buffalo_l",
            root=insightface_root,
            providers=providers,
        )
        ctx.face_app.prepare(ctx_id=ctx_id, det_size=(640, 640))
        return ctx.face_app

    @staticmethod
    def _detect_faces(face_app, pil_image: Image.Image):
        """PIL Image → BGR numpy → insightface face detection."""
        face_np = np.array(pil_image)
        face_np = face_np[:, :, ::-1]  # RGB → BGR
        faces = face_app.get(face_np)
        return faces if len(faces) > 0 else None

    @staticmethod
    def _build_faceid_embed(face, pipe, ctx: GenerationContext) -> torch.Tensor:
        """
        Build FaceID embedding tensor.

        normed_embedding (512,) numpy → (2, 1, 512) torch tensor
        dim0 = [negative (zeros), positive] for classifier_free_guidance.
        """
        positive_embed = (
            torch.from_numpy(face.normed_embedding)
            .unsqueeze(0)
            .unsqueeze(0)
        )  # (1, 1, 512)
        positive_embed = positive_embed.to(ctx.device, dtype=pipe.unet.dtype)

        negative_embed = torch.zeros_like(positive_embed)
        face_id_embed = torch.cat([negative_embed, positive_embed], dim=0)
        # shape: (2, 1, 512)
        logger.debug(f"FaceID embed built, shape={face_id_embed.shape}")
        return face_id_embed


# ---------------------------------------------------------------------------
# FaceID-Plus strategy (extends FaceID with CLIP ViT-H/14)
# ---------------------------------------------------------------------------

class FaceIDPlusStrategy(FaceIDStrategy):
    """
    IP-Adapter-FaceID-Plus (insightface 512-dim + CLIP ViT-H/14 ~3.94 GB).

    Inherits all FaceID logic and adds CLIP hidden-state extraction.
    The CLIP embeds are set to `pipe.unet.encoder_hid_proj.image_projection.clip_embeds`
    so that `IPAdapterFaceIDImageProjection.forward()` can use both id_embeds and clip_embeds.
    """

    name = "faceid-plus"

    # Cached CLIPImageProcessor (reused across calls; crop_size is fixed per model)
    _clip_processor: Optional[CLIPImageProcessor] = None

    def get_model_config(self) -> ModelConfig:
        return replace(
            super().get_model_config(),
            weight_name="ip-adapter-faceid-plus_sd15.bin",
            image_encoder_folder="ip-adapter-faceid-plus_sd15/image_encoder",
            default_scale_range=(0.7, 1.0),
        )

    # -- dependency check ---------------------------------------------------

    def check_dependencies(self, ctx: GenerationContext) -> Tuple[bool, str]:
        # FaceID base dependencies
        ok, reason = super().check_dependencies(ctx)
        if not ok:
            return (False, reason)

        # CLIP ViT-H/14 model files
        hf_cache = Path(settings.HF_HUB_CACHE_PATH).resolve()
        faceid_cache = hf_cache / "models--h94--IP-Adapter-FaceID" / "snapshots"

        if not faceid_cache.exists():
            return (
                False,
                "IP-Adapter-FaceID model cache not found "
                "(download h94/IP-Adapter-FaceID first)",
            )

        snapshots = list(faceid_cache.iterdir())
        if not snapshots:
            return (
                False,
                "IP-Adapter-FaceID snapshots directory is empty",
            )

        clip_path = snapshots[0] / "ip-adapter-faceid-plus_sd15" / "image_encoder"
        if not clip_path.exists():
            return (
                False,
                "CLIP ViT-H/14 not found inside IP-Adapter-FaceID cache "
                "(~3.94 GB required, download image_encoder/ subfolder)",
            )

        return (True, "")

    # -- embedding extraction -----------------------------------------------

    def prepare_embeddings(
        self,
        pipe,
        ctx: GenerationContext,
    ) -> Optional[Dict[str, Any]]:
        # 1. FaceID embedding (reuse parent logic)
        result = super().prepare_embeddings(pipe, ctx)
        if result is None:
            return None  # Face detection failed, trigger fallback

        # 2. CLIP hidden states (exception → fallback to Original)
        try:
            clip_embeds = self._extract_clip_embeds(pipe, ctx.ref_images[0], ctx)
        except Exception as e:
            logger.warning(f"[faceid-plus] CLIP extraction failed: {e}, falling back")
            return None

        # 3. Set clip_embeds into the projection layer
        #    encoder_hid_proj is MultiIPAdapterImageProjection;
        #    individual layers live in image_projection_layers (ModuleList).
        #    Repeat along batch dim to match CFG-duplicated faceid embeds (bs=2).
        proj = pipe.unet.encoder_hid_proj.image_projection_layers[0]
        faceid_bs = result["ip_adapter_image_embeds"][0].shape[0]
        proj.clip_embeds = clip_embeds.repeat(faceid_bs, 1, 1, 1)
        logger.debug(f"FaceID-Plus: clip_embeds set (bs={faceid_bs}) to projection layer")

        return result  # ip_adapter_image_embeds unchanged

    # -- CLIP helpers -------------------------------------------------------

    @classmethod
    def _get_clip_processor(cls, crop_size: int) -> CLIPImageProcessor:
        """Return a cached CLIPImageProcessor (created once, reused)."""
        if cls._clip_processor is None:
            cls._clip_processor = CLIPImageProcessor(
                do_resize=True,
                size={"shortest_edge": crop_size},
                do_center_crop=True,
                crop_size=crop_size,
                do_normalize=True,
            )
        return cls._clip_processor

    @staticmethod
    def _extract_clip_embeds(pipe, pil_image: Image.Image, ctx: GenerationContext) -> torch.Tensor:
        """
        PIL Image → CLIPImageProcessor → image_encoder → CLIP hidden states.

        Returns tensor of shape (1, 1, N, 1280) on ctx.device/dtype.
        IPAdapterFaceIDImageProjection.forward expects 4-D: (bs, num_images, seq, hidden).
        """
        image_encoder = pipe.image_encoder       # CLIPVisionModelWithProjection

        # pipe.image_processor is VaeImageProcessor (not callable for CLIP),
        # so use transformers.CLIPImageProcessor with the encoder's crop_size.
        crop_size = image_encoder.config.image_size
        clip_processor = FaceIDPlusStrategy._get_clip_processor(crop_size)

        pixel_values = clip_processor(
            images=pil_image, return_tensors="pt"
        ).pixel_values.to(ctx.device, dtype=image_encoder.dtype)

        with torch.no_grad():
            clip_outputs = image_encoder(pixel_values)
            # Use last_hidden_state (full sequence) rather than pooler_output
            hidden_states = clip_outputs.last_hidden_state  # (1, N, 1280)

        # Add num_images dim → (1, 1, N, 1280) for IPAdapterFaceIDImageProjection
        return hidden_states.unsqueeze(1).to(ctx.device, dtype=pipe.unet.dtype)


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

class IPAdapterStrategyRegistry:
    """
    Registry mapping mode name → strategy class.

    Unknown mode names fall back to OriginalIPAdapterStrategy with a warning.
    """

    _registry: Dict[str, type] = {
        "original": OriginalIPAdapterStrategy,
        "faceid": FaceIDStrategy,
        "faceid-plus": FaceIDPlusStrategy,
    }

    @classmethod
    def get(cls, mode: str) -> IPAdapterStrategy:
        strategy_cls = cls._registry.get(mode)
        if strategy_cls is None:
            logger.warning(
                f"Unknown IP-Adapter mode '{mode}', falling back to 'original'. "
                f"Available modes: {list(cls._registry.keys())}"
            )
            strategy_cls = OriginalIPAdapterStrategy
        return strategy_cls()

    @classmethod
    def available_modes(cls) -> List[str]:
        return list(cls._registry.keys())
