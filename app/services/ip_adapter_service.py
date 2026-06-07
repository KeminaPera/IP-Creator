"""
IP-Adapter Service

Provides character consistency for image generation using IP-Adapter.
Encodes reference images into image prompt embeddings that guide
the diffusion model to maintain character appearance.

IP-Adapter is ideal for:
- Instant character consistency without LoRA training
- Using IP Asset reference images for generation
- Complementing LoRA for even better results
"""
import os
import io
import traceback

# ⚠️ 必须在import torch之前设置环境变量，确保Celery worker能正确使用MPS
if os.environ.get('OBJC_DISABLE_INITIALIZE_FORK_SAFETY') != 'YES':
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
    
if os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') != '1':
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

import numpy as np
import torch
from typing import Optional, Dict, Any, List
from pathlib import Path
from PIL import Image
from app.config.settings import settings
from app.utils.logger import logger
from app.core.gpu_cache import gpu_cache
from app.utils.prompt_analyzer import prompt_analyzer
from app.services.clip_similarity import CLIPSimilarityCalculator
from app.services.ip_adapter_strategies import (
    GenerationContext,
    IPAdapterStrategy,
    IPAdapterStrategyRegistry,
    OriginalIPAdapterStrategy,
    FaceIDStrategy,
)

# 清除GPU缓存，确保Celery worker进程重新检测MPS
gpu_cache.invalidate()


class IPAdapterService:
    """
    Service for IP-Adapter based character consistency.
    
    Uses IP-Adapter to encode reference images and inject them
    into the diffusion process for consistent character generation.
    """
    
    def __init__(self):
        """Initialize IP-Adapter service."""
        # Use cached GPU info to avoid redundant torch.cuda.is_available() checks
        gpu_info = gpu_cache.get_info()
        
        # ✅ 支持Apple Silicon MPS
        device_type = gpu_info.get("device_type", "cpu")
        if device_type == "mps":
            self.device = "mps"
            self.dtype = torch.float32  # ⚠️ MPS必须使用float32，float16会导致问题
        elif gpu_info["cuda_available"]:
            self.device = "cuda"
            self.dtype = torch.float16
        else:
            self.device = "cpu"
            self.dtype = torch.float32
        
        # Strategy pattern pipeline cache (replaces _ip_adapter_pipe)
        self._base_pipe = None              # SD 1.5 base pipeline (always reused)
        self._loaded_strategy_name = None   # Currently loaded IP-Adapter strategy name
        self._face_app = None               # insightface.FaceAnalysis instance (cross-strategy reuse)
        
        self.models_path = Path(settings.MODELS_PATH)
        self.clip_calculator = CLIPSimilarityCalculator()
        
        # Log current IP-Adapter mode
        mode = self._get_adapter_mode()
        logger.info(
            f"IPAdapterService initialized on {self.device} with {self.dtype}, "
            f"mode={mode}"
        )
    
    def _get_adapter_mode(self) -> str:
        """
        Resolve the active IP-Adapter mode from environment or settings.
    
        Priority: IP_ADAPTER_MODE env var > settings.IP_ADAPTER_MODE > "original"
        """
        env_mode = os.environ.get("IP_ADAPTER_MODE", "").strip().lower()
        if env_mode:
            return env_mode
        settings_mode = getattr(settings, "IP_ADAPTER_MODE", "").strip().lower()
        return settings_mode or "original"
    
    def _resolve_strategy(self) -> IPAdapterStrategy:
        """Resolve the active IP-Adapter strategy from configuration."""
        mode = self._get_adapter_mode()
        return IPAdapterStrategyRegistry.get(mode)
    
    def _ensure_pipeline(self, strategy: IPAdapterStrategy) -> Any:
        """
        Ensure the pipeline has the correct IP-Adapter weights loaded
        for the given strategy.
    
        SD 1.5 base pipeline (~2 GB) is always reused; only IP-Adapter weights
        are swapped when switching strategies.
    
        Exception safety: if unload_ip_adapter() fails, force-rebuilds base pipeline.
        """
        if self._loaded_strategy_name == strategy.name and self._base_pipe is not None:
            return self._base_pipe  # Already loaded, reuse
    
        from diffusers import StableDiffusionPipeline
    
        # Unload previous IP-Adapter weights if switching strategies
        if self._base_pipe is not None and self._loaded_strategy_name is not None:
            try:
                self._base_pipe.unload_ip_adapter()
                logger.info(f"Unloaded previous IP-Adapter weights ({self._loaded_strategy_name})")
            except Exception as e:
                logger.warning(
                    f"unload_ip_adapter() failed ({self._loaded_strategy_name}): {e}, "
                    "rebuilding base pipeline from scratch"
                )
                self._base_pipe = None  # Force rebuild
    
        # Load base SD 1.5 pipeline if not yet cached
        if self._base_pipe is None:
            model_id = "runwayml/stable-diffusion-v1-5"
            _cache_root = Path(settings.HF_HUB_CACHE_PATH).resolve()
            _sd_model_dir = _cache_root / "models--runwayml--stable-diffusion-v1-5" / "snapshots"
            _local_model_path = model_id
            if _sd_model_dir.exists():
                _snapshots = list(_sd_model_dir.iterdir())
                if _snapshots:
                    _local_model_path = str(_snapshots[0])
                    logger.info(f"Using local SD 1.5 model: {_local_model_path}")
    
            logger.info("Loading SD 1.5 base pipeline...")
            self._base_pipe = StableDiffusionPipeline.from_pretrained(
                _local_model_path,
                torch_dtype=self.dtype,
                safety_checker=None,
                requires_safety_checker=False,
                local_files_only=True,
            )

            # Replace default PNDMScheduler with DPM++ 2M Karras
            # Better quality per step, especially for facial details
            from diffusers import DPMSolverMultistepScheduler
            self._base_pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self._base_pipe.scheduler.config,
                use_karras_sigmas=True,
                algorithm_type="dpmsolver++",
            )
            logger.info("Scheduler: DPMSolver++ 2M Karras")

            self._base_pipe = self._base_pipe.to(self.device)
            if self.device == "mps":
                logger.info("Attention slicing disabled for MPS (IP-Adapter compatibility)")
    
        # Load IP-Adapter weights for the current strategy
        config = strategy.get_model_config()
        logger.info(
            f"Loading IP-Adapter weights: {config.weight_name} "
            f"(repo={config.repo}, mode={strategy.name})"
        )
    
        # Find local cache path for IP-Adapter weights
        cache_locations = [
            Path(settings.HF_HUB_CACHE_PATH) / config.cache_dir_name,
            *(
                [Path(os.environ['HF_HUB_CACHE']) / config.cache_dir_name]
                if os.environ.get('HF_HUB_CACHE') else []
            ),
            Path.home() / ".cache" / "huggingface" / "hub" / config.cache_dir_name,
        ]
    
        local_ip_adapter_path = next(
            (p for p in cache_locations if p and p.exists()), None
        )
    
        if local_ip_adapter_path:
            snapshots_dir = local_ip_adapter_path / "snapshots"
            if not snapshots_dir.exists():
                raise FileNotFoundError(f"Snapshots directory not found: {snapshots_dir}")
            snapshots = list(snapshots_dir.iterdir())
            if not snapshots:
                raise FileNotFoundError(f"No snapshots found in {snapshots_dir}")
            snapshot_path = snapshots[0]
            logger.info(f"Loading IP-Adapter from local cache: {snapshot_path}")
            self._base_pipe.load_ip_adapter(
                str(snapshot_path),
                subfolder=config.subfolder,
                weight_name=config.weight_name,
                image_encoder_folder=config.image_encoder_folder,
            )
        else:
            logger.info(f"Local cache not found, loading IP-Adapter from Hub: {config.repo}")
            self._base_pipe.load_ip_adapter(
                config.repo,
                subfolder=config.subfolder,
                weight_name=config.weight_name,
                image_encoder_folder=config.image_encoder_folder,
            )
    
        self._loaded_strategy_name = strategy.name
        logger.info(f"IP-Adapter loaded successfully (mode={strategy.name})")
        return self._base_pipe

    @staticmethod
    def _cleanup_clip_embeds(pipe) -> None:
        """
        Release clip_embeds tensors from IP-Adapter projection layers.

        FaceID-Plus stores clip_embeds as a module attribute on the projection
        layer. Without cleanup, the GPU tensor persists between calls (~1.3 MB
        at fp16). Setting to None frees the reference for GC.
        """
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
            pass  # Best-effort cleanup; never block generation
    
    @staticmethod
    def _ensure_face_app_for_service(ctx: GenerationContext):
        """
        Ensure insightface FaceAnalysis is loaded for face detection.

        Called from the service level (before strategy execution) to enable
        face detection on original images for face-aware cropping.
        """
        if ctx.face_app is not None:
            return ctx.face_app

        from insightface.app import FaceAnalysis

        # Resolve insightface model root
        project_root = Path(__file__).resolve().parent.parent.parent
        insightface_root = str(project_root / "data" / "models" / "insightface")
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
    def _detect_faces_in_image(
        face_app,
        image: Image.Image,
    ) -> Optional[list]:
        """
        Detect faces in a PIL image using insightface.

        Args:
            face_app: insightface.FaceAnalysis instance
            image: Original PIL Image (before any resizing)

        Returns:
            List of detected face objects, or None if no faces found.
        """
        img_np = np.array(image)
        img_np = img_np[:, :, ::-1]  # RGB → BGR
        faces = face_app.get(img_np)
        return faces if len(faces) > 0 else None

    @staticmethod
    def _crop_face_region(
        image: Image.Image,
        face_bbox: tuple,
        target_size: int = 512,
        padding_factor: float = 1.5,
    ) -> Image.Image:
        """
        Crop and resize the face region from the image.

        Expands the face bounding box by padding_factor to include surrounding
        context (hair, neck), then resizes to target_size×target_size.

        Args:
            image: Original PIL Image
            face_bbox: (x1, y1, x2, y2) bounding box from insightface
            target_size: Output image size (square)
            padding_factor: Expansion factor around face bbox (1.5 = 50% padding)

        Returns:
            Cropped and resized PIL Image (target_size × target_size)
        """
        x1, y1, x2, y2 = face_bbox
        w, h = image.size

        # Calculate face center and expanded box
        face_cx = (x1 + x2) / 2
        face_cy = (y1 + y2) / 2
        face_w = x2 - x1
        face_h = y2 - y1
        face_side = max(face_w, face_h)

        # Expand to include hair/neck/shoulders context
        expanded = face_side * padding_factor
        half = expanded / 2

        # Compute crop box (clamped to image boundaries)
        crop_x1 = max(0, int(face_cx - half))
        crop_y1 = max(0, int(face_cy - half))
        crop_x2 = min(w, int(face_cx + half))
        crop_y2 = min(h, int(face_cy + half))

        # Make square crop
        crop_w = crop_x2 - crop_x1
        crop_h = crop_y2 - crop_y1
        crop_side = max(crop_w, crop_h)

        # Re-center the square crop
        crop_cx = (crop_x1 + crop_x2) / 2
        crop_cy = (crop_y1 + crop_y2) / 2
        crop_x1 = max(0, int(crop_cx - crop_side / 2))
        crop_y1 = max(0, int(crop_cy - crop_side / 2))
        crop_x2 = crop_x1 + crop_side
        crop_y2 = crop_y1 + crop_side

        # Clamp to image bounds
        if crop_x2 > w:
            crop_x2 = w
            crop_x1 = max(0, crop_x2 - crop_side)
        if crop_y2 > h:
            crop_y2 = h
            crop_y1 = max(0, crop_y2 - crop_side)

        cropped = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))

        # Resize to target size with high quality
        return cropped.resize((target_size, target_size), Image.Resampling.LANCZOS)

    def preprocess_reference_image(
        self,
        image_path: str,
        target_size: int = 512,
        face_bbox: Optional[tuple] = None,
    ) -> Image.Image:
        """
        Preprocess a reference image for IP-Adapter.

        If a face bounding box is provided, crops around the face region
        (face-aware cropping). Otherwise falls back to center crop.

        Args:
            image_path: Path to reference image
            target_size: Target size for the image
            face_bbox: Optional (x1, y1, x2, y2) from insightface detection

        Returns:
            Preprocessed PIL Image
        """
        image = Image.open(image_path).convert("RGB")

        if face_bbox is not None:
            # Face-aware crop: expand around face and resize
            logger.info(
                f"Using face-aware crop: bbox={face_bbox}, "
                f"original_size={image.size}"
            )
            return self._crop_face_region(image, face_bbox, target_size)

        # Fallback: resize maintaining aspect ratio + center crop
        w, h = image.size
        scale = target_size / max(w, h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Center crop to square
        left = (new_w - target_size) // 2
        top = (new_h - target_size) // 2
        right = left + target_size
        bottom = top + target_size

        # If image is smaller than target, pad it
        if new_w < target_size or new_h < target_size:
            padded = Image.new("RGB", (target_size, target_size), (255, 255, 255))
            paste_x = (target_size - new_w) // 2
            paste_y = (target_size - new_h) // 2
            padded.paste(image, (paste_x, paste_y))
            image = padded
        else:
            image = image.crop((left, top, right, bottom))

        return image
    
    async def generate_with_ip_adapter(
        self,
        prompt: str,
        reference_images: List[str],
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 30,
        cfg_scale: float = 7.0,
        ip_adapter_scale: float = 0.7,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate image with IP-Adapter for character consistency.

        Delegates to the active strategy (Original / FaceID / FaceID-Plus).
        Falls back to OriginalIPAdapterStrategy on dependency or embedding failure.

        For FaceID/FaceID-Plus modes, face detection is performed on the
        ORIGINAL image before preprocessing, enabling face-aware cropping
        for much higher facial detail in the reference.

        Args:
            prompt: Text prompt for generation
            reference_images: List of paths to reference images
            negative_prompt: Negative prompt
            width: Image width
            height: Image height
            steps: Sampling steps
            cfg_scale: CFG guidance scale
            ip_adapter_scale: IP-Adapter weight (0.0-1.0)
            seed: Random seed

        Returns:
            Dictionary with image bytes and metadata
        """
        try:
            # 1. Resolve active strategy
            strategy = self._resolve_strategy()

            # 2. Build minimal context for dependency check
            ctx = GenerationContext(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg_scale=cfg_scale,
                seed=seed,
                ip_adapter_scale=ip_adapter_scale,
                ref_images=[],
                device=self.device,
                dtype=self.dtype,
                face_app=self._face_app,
            )

            # 3. Dependency check (fallback to Original if unsatisfied)
            ok, reason = strategy.check_dependencies(ctx)
            if not ok:
                logger.warning(
                    f"[{strategy.name}] dependency check failed: {reason}, "
                    "falling back to original"
                )
                strategy = OriginalIPAdapterStrategy()

            # 4. For FaceID modes: detect faces in ORIGINAL images before preprocessing
            #    This enables face-aware cropping AND pre-detected faces for embedding
            needs_face_detection = isinstance(strategy, FaceIDStrategy)
            detected_faces = None
            primary_face_bbox = None

            if needs_face_detection and reference_images:
                face_app = self._ensure_face_app_for_service(ctx)
                first_img_path = reference_images[0]
                if Path(first_img_path).exists():
                    original_img = Image.open(first_img_path).convert("RGB")
                    detected_faces = self._detect_faces_in_image(
                        face_app, original_img
                    )
                    if detected_faces:
                        primary_face_bbox = tuple(detected_faces[0].bbox)
                        logger.info(
                            f"Pre-detected face in original image: "
                            f"bbox={primary_face_bbox}, "
                            f"image_size={original_img.size}, "
                            f"confidence={detected_faces[0].det_score:.3f}"
                        )
                    else:
                        logger.warning(
                            "No face detected in original image, "
                            "will attempt detection after preprocessing"
                        )
                    # Write back face_app for cross-call reuse
                    self._face_app = ctx.face_app

            # 5. Preprocess reference images (face-aware if face detected)
            ref_images = []
            for img_path in reference_images:
                if Path(img_path).exists():
                    ref_images.append(
                        self.preprocess_reference_image(
                            img_path, face_bbox=primary_face_bbox
                        )
                    )
                else:
                    logger.warning(f"Reference image not found: {img_path}")

            if not ref_images:
                return {"status": "failed", "error": "No valid reference images provided"}

            # 6. Update context with preprocessed images and detected faces
            ctx = GenerationContext(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                cfg_scale=cfg_scale,
                seed=seed,
                ip_adapter_scale=ip_adapter_scale,
                ref_images=ref_images,
                device=self.device,
                dtype=self.dtype,
                face_app=self._face_app,
                detected_faces=detected_faces,
            )

            # 7. Ensure pipeline has correct IP-Adapter weights
            pipe = self._ensure_pipeline(strategy)

            # 8. Validate and set IP-Adapter scale
            config = strategy.get_model_config()
            ip_adapter_scale = strategy.validate_scale(ip_adapter_scale, config)
            try:
                pipe.set_ip_adapter_scale(ip_adapter_scale)
            except Exception as e:
                logger.warning(f"Could not set IP-Adapter scale: {e}")

            # 9. Extract embeddings via strategy
            adapter_kwargs = strategy.prepare_embeddings(pipe, ctx)
            if adapter_kwargs is None:
                # Embedding extraction failed, fall back to Original
                logger.warning(
                    f"[{strategy.name}] embedding extraction failed, "
                    "falling back to original"
                )
                strategy = OriginalIPAdapterStrategy()
                pipe = self._ensure_pipeline(strategy)
                config = strategy.get_model_config()
                ip_adapter_scale = strategy.validate_scale(ip_adapter_scale, config)
                try:
                    pipe.set_ip_adapter_scale(ip_adapter_scale)
                except Exception as e:
                    logger.warning(f"Could not set IP-Adapter scale (fallback): {e}")
                # Original strategy doesn't need detected_faces
                ctx.detected_faces = None
                adapter_kwargs = strategy.prepare_embeddings(pipe, ctx)

            # 10. Write back face_app to service (for cross-call reuse)
            self._face_app = ctx.face_app

            # 11. Build gen_kwargs and run generation
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)

            gen_kwargs = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "num_inference_steps": steps,
                "guidance_scale": cfg_scale,
                "generator": generator,
                "num_images_per_prompt": 1,
                **adapter_kwargs,
            }

            logger.info(
                f"Generating with [{strategy.name}]: {prompt[:50]}... "
                f"({len(ref_images)} ref image(s), scale={ip_adapter_scale:.2f})"
            )

            try:
                result = pipe(**gen_kwargs)
            finally:
                # Always clean up clip_embeds from projection layer (free GPU memory)
                self._cleanup_clip_embeds(pipe)

            image = result.images[0]

            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            logger.info(f"IP-Adapter [{strategy.name}] generation successful")

            return {
                "status": "success",
                "image_bytes": img_byte_arr.getvalue(),
                "parameters": {
                    "prompt": prompt,
                    "reference_images": reference_images,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg_scale": cfg_scale,
                    "ip_adapter_scale": ip_adapter_scale,
                    "ip_adapter_mode": strategy.name,
                    "seed": seed,
                    "face_crop": primary_face_bbox is not None,
                },
            }

        except Exception as e:
            logger.error(f"IP-Adapter generation failed: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return {"status": "failed", "error": str(e)}
    
    async def generate_with_lora_and_ip(
        self,
        prompt: str,
        reference_images: List[str],
        lora_path: Optional[str] = None,
        lora_weight: float = 0.7,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 30,
        cfg_scale: float = 7.0,
        ip_adapter_scale: float = 0.6,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate image with both LoRA and IP-Adapter for maximum consistency.

        Combines LoRA (for style) + IP-Adapter (for character face/body).

        Note: FaceID / FaceID-Plus modes are incompatible with LoRA+IP-Adapter
        because FaceID requires insightface embeddings (not PIL images). When the
        active strategy does not support LoRA, this method automatically falls
        back to OriginalIPAdapterStrategy.

        Args:
            prompt: Text prompt
            reference_images: Reference image paths
            lora_path: Path to LoRA weights
            lora_weight: LoRA weight
            negative_prompt: Negative prompt
            width: Image width
            height: Image height
            steps: Sampling steps
            cfg_scale: CFG guidance scale
            ip_adapter_scale: IP-Adapter weight
            seed: Random seed

        Returns:
            Dictionary with image bytes and metadata
        """
        try:
            # 1. Resolve strategy; fall back to Original if LoRA-incompatible
            strategy = self._resolve_strategy()
            if not strategy.supports_lora():
                logger.info(
                    f"[{strategy.name}] incompatible with LoRA, using original IP-Adapter"
                )
                strategy = OriginalIPAdapterStrategy()

            # 2. Ensure pipeline
            pipe = self._ensure_pipeline(strategy)

            # 3. Load LoRA weights
            if lora_path and Path(lora_path).exists():
                try:
                    pipe.load_lora_weights(lora_path)
                    pipe.fuse_lora(lora_scale=lora_weight)
                    logger.info(f"Loaded LoRA: {lora_path} with weight {lora_weight}")
                except Exception as e:
                    logger.warning(f"Failed to load LoRA: {e}")

            # 4. Preprocess reference images
            ref_images = []
            for img_path in reference_images:
                if Path(img_path).exists():
                    ref_images.append(self.preprocess_reference_image(img_path))

            if not ref_images:
                return {"status": "failed", "error": "No valid reference images provided"}

            # 5. Validate and set IP-Adapter scale
            config = strategy.get_model_config()
            ip_adapter_scale = strategy.validate_scale(ip_adapter_scale, config)
            try:
                pipe.set_ip_adapter_scale(ip_adapter_scale)
            except Exception as e:
                logger.warning(f"Failed to set IP-Adapter scale: {e}")

            # 6. Build gen_kwargs (Original mode: pass PIL images directly)
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)

            logger.info(
                f"Generating with LoRA + [{strategy.name}]: {prompt[:50]}..."
            )

            lora_loaded = bool(lora_path and Path(lora_path).exists())
            try:
                result = pipe(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    ip_adapter_image=ref_images[0] if len(ref_images) == 1 else ref_images,
                    width=width,
                    height=height,
                    num_inference_steps=steps,
                    guidance_scale=cfg_scale,
                    generator=generator,
                    num_images_per_prompt=1,
                )

                image = result.images[0]

                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
            finally:
                # 7. Always unload LoRA weights (even on generation failure)
                if lora_loaded:
                    try:
                        pipe.unfuse_lora()
                        pipe.unload_lora_weights()
                    except Exception as e:
                        logger.warning(f"Failed to unload LoRA weights: {e}")

            logger.info(f"LoRA + [{strategy.name}] generation successful")

            return {
                "status": "success",
                "image_bytes": img_byte_arr.getvalue(),
                "parameters": {
                    "prompt": prompt,
                    "reference_images": reference_images,
                    "lora_path": lora_path,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg_scale": cfg_scale,
                    "ip_adapter_scale": ip_adapter_scale,
                    "ip_adapter_mode": strategy.name,
                    "lora_weight": lora_weight,
                    "seed": seed,
                },
            }

        except Exception as e:
            logger.error(f"LoRA + IP-Adapter generation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def analyze_prompt(self, prompt: str) -> Dict[str, str]:
        """
        Analyze prompt to extract generation attributes.
        
        Args:
            prompt: Generation prompt
            
        Returns:
            Dictionary with angle, expression, pose, scene_context, environment
        """
        return prompt_analyzer.analyze_prompt(prompt)
    
    def select_best_reference_images(
        self,
        reference_images: List[Dict[str, Any]],
        prompt: str,
        max_images: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Intelligently select reference images matching prompt attributes.
        
        Algorithm:
        1. Parse prompt for angle/expression/pose keywords
        2. Score each reference image by attribute match
        3. Select top-N images with diversity
        4. Assign weights: primary (60%), secondary (30%), style (10%)
        
        Args:
            reference_images: List of image dicts with angle/expression metadata
                Format: [{"path": "/path/img.jpg", "angle": "front", "expression": "happy"}, ...]
            prompt: Generation prompt
            max_images: Maximum number of reference images to select
            
        Returns:
            Selected images with assigned weights:
            [{"path": str, "weight": float, "rank": int}, ...]
        """
        if not reference_images:
            logger.warning("No reference images provided for selection")
            return []
        
        # Step 1: Analyze prompt attributes
        prompt_attrs = prompt_analyzer.analyze_prompt(prompt)
        logger.info(f"Prompt attributes: {prompt_attrs}")
        
        # Step 2: Score each reference image
        scored_images = []
        for img in reference_images:
            # Extract image attributes
            img_attrs = {
                "angle": img.get("angle", "unknown"),
                "expression": img.get("expression", "unknown"),
                "pose": img.get("pose", "unknown"),
            }
            
            # Calculate similarity score
            score = prompt_analyzer.calculate_similarity_score(prompt_attrs, img_attrs)
            
            scored_images.append({
                "path": img["path"],
                "score": score,
                "attributes": img_attrs,
                "original": img,
            })
        
        # Step 3: Sort by score (descending)
        scored_images.sort(key=lambda x: x["score"], reverse=True)
        
        # Step 4: Select top-N images with diversity
        selected = []
        for i, img_data in enumerate(scored_images[:max_images]):
            # Assign weights based on rank
            if i == 0:
                weight = 0.60  # Primary reference
            elif i == 1:
                weight = 0.30  # Secondary reference
            else:
                weight = 0.10  # Style reference
            
            selected.append({
                "path": img_data["path"],
                "weight": weight,
                "rank": i + 1,
                "score": img_data["score"],
                "attributes": img_data["attributes"],
            })
        
        logger.info(f"Selected {len(selected)} reference images for prompt")
        for img in selected:
            logger.debug(f"  Rank {img['rank']}: {img['path']} (score: {img['score']:.2f}, weight: {img['weight']})")
        
        return selected
    
    def calculate_adaptive_scale(
        self,
        prompt: str,
        use_lora: bool = False,
    ) -> float:
        """
        Calculate optimal IP-Adapter scale based on prompt analysis.
        
        Rules:
        - Character emphasis (character name, face, portrait) → 0.7-0.9
        - Scene emphasis (landscape, background, environment) → 0.5-0.7
        - Creative freedom (fantasy, abstract, surreal) → 0.3-0.5
        - Action/dynamic scenes → 0.6-0.8
        - If LoRA is used, slightly reduce IP-Adapter scale (avoid overfitting)
        
        Args:
            prompt: Generation prompt
            use_lora: Whether LoRA is also being used
            scenario: Generation scenario type
            
        Returns:
            Optimal scale value (0.0-1.0)
        """
        # Analyze prompt
        attrs = prompt_analyzer.analyze_prompt(prompt)
        
        # Base scale determination
        base_scale = 0.7  # Default
        
        # Character-focused prompts need higher IP-Adapter weight
        if attrs["scene_context"] == "character":
            if attrs["angle"] in ["closeup", "front"]:
                base_scale = 0.85  # Very high for close-up portraits
            else:
                base_scale = 0.75  # High for character shots
        
        # Scene-focused prompts need lower IP-Adapter weight
        elif attrs["scene_context"] == "scene":
            base_scale = 0.60
        
        # Action scenes need moderate-high weight
        elif attrs["scene_context"] == "action":
            base_scale = 0.70
        
        # Mixed context
        elif attrs["scene_context"] == "mixed":
            base_scale = 0.65
        
        # Adjust for LoRA usage (reduce to avoid overfitting)
        if use_lora:
            base_scale *= 0.85  # 15% reduction
        
        # Adjust for environment
        if attrs["environment"] == "outdoor":
            base_scale *= 0.95  # Slight reduction for outdoor scenes
        
        # Clamp to valid range
        final_scale = max(0.3, min(1.0, base_scale))
        
        logger.info(
            f"Adaptive IP-Adapter scale: {final_scale:.2f} "
            f"(context: {attrs['scene_context']}, lora: {use_lora}, env: {attrs['environment']})"
        )
        
        return round(final_scale, 2)
    
    async def check_generated_consistency(
        self,
        generated_image_path: str,
        reference_images: List[str],
        threshold: float = 0.75,
    ) -> Dict[str, Any]:
        """
        Check consistency between generated image and reference images.
        
        Uses CLIP similarity to measure character consistency.
        
        Args:
            generated_image_path: Path to generated image
            reference_images: List of reference image paths
            threshold: Minimum similarity score for consistency (0.0-1.0)
            
        Returns:
            {
                "consistent": bool,
                "similarity_score": float,
                "passed": bool,
                "warning": str | None,
                "recommendation": str | None
            }
        """
        try:
            # Check if files exist
            if not Path(generated_image_path).exists():
                return {
                    "consistent": False,
                    "similarity_score": 0.0,
                    "passed": False,
                    "warning": "Generated image file not found",
                    "recommendation": "Check generation output path",
                }
            
            valid_refs = [ref for ref in reference_images if Path(ref).exists()]
            if not valid_refs:
                return {
                    "consistent": False,
                    "similarity_score": 0.0,
                    "passed": False,
                    "warning": "No valid reference images found",
                    "recommendation": "Ensure reference images are accessible",
                }
            
            # Calculate CLIP similarity
            # Use the first reference image as primary reference
            primary_ref = valid_refs[0]
            similarities = self.clip_calculator.calculate_batch_similarity(
                reference_path=primary_ref,
                test_paths=[generated_image_path],
            )
            
            similarity_score = similarities[0] if similarities else 0.0
            
            # If multiple references, average the scores
            if len(valid_refs) > 1:
                all_scores = []
                for ref in valid_refs:
                    scores = self.clip_calculator.calculate_batch_similarity(
                        reference_path=ref,
                        test_paths=[generated_image_path],
                    )
                    all_scores.extend(scores)
                similarity_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
            
            passed = similarity_score >= threshold
            
            # Generate warning and recommendation
            warning = None
            recommendation = None
            
            if not passed:
                warning = f"Low consistency score: {similarity_score:.2f} (threshold: {threshold:.2f})"
                
                if similarity_score < 0.5:
                    recommendation = (
                        "Consistency is very low. Consider: "
                        "1) Using more reference images, "
                        "2) Increasing IP-Adapter scale, "
                        "3) Adding the character's trigger word to the prompt"
                    )
                elif similarity_score < threshold:
                    recommendation = (
                        "Consistency is below threshold. Try: "
                        "1) Adjusting IP-Adapter scale higher, "
                        "2) Using different reference images, "
                        "3) Simplifying the prompt to focus on the character"
                    )
            else:
                if similarity_score >= 0.85:
                    recommendation = "Excellent consistency! The generated image closely matches the character."
                else:
                    recommendation = "Good consistency. The character is recognizable."
            
            result = {
                "consistent": passed,
                "similarity_score": round(similarity_score, 4),
                "passed": passed,
                "warning": warning,
                "recommendation": recommendation,
                "threshold": threshold,
            }
            
            logger.info(
                f"Consistency check: {'PASSED' if passed else 'FAILED'} "
                f"(score: {similarity_score:.4f}, threshold: {threshold:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            return {
                "consistent": False,
                "similarity_score": 0.0,
                "passed": False,
                "warning": f"Consistency check error: {str(e)}",
                "recommendation": "Try generation again or check image files",
            }


# Global IP-Adapter service instance
ip_adapter_service = IPAdapterService()
