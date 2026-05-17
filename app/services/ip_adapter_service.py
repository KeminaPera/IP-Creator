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

# ⚠️ 必须在import torch之前设置环境变量，确保Celery worker能正确使用MPS
if os.environ.get('OBJC_DISABLE_INITIALIZE_FORK_SAFETY') != 'YES':
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
    
if os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') != '1':
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

import torch
from typing import Optional, Dict, Any, List
from pathlib import Path
from PIL import Image
from app.config.settings import settings
from app.utils.logger import logger
from app.core.gpu_cache import gpu_cache
from app.utils.prompt_analyzer import prompt_analyzer, PromptAnalyzer
from app.services.clip_similarity import CLIPSimilarityCalculator

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
        
        self._ip_adapter_pipe = None
        self._image_encoder = None
        self.models_path = Path(settings.MODELS_PATH)
        self.clip_calculator = CLIPSimilarityCalculator()
        
        logger.info(f"IPAdapterService initialized on {self.device} with {self.dtype}")
    
    def _get_ip_adapter_pipeline(self):
        """
        Lazy-load IP-Adapter pipeline.
        
        Uses StableDiffusionPipeline with IP-Adapter support.
        Falls back to standard pipeline if IP-Adapter not available.
        """
        if self._ip_adapter_pipe is None:
            try:
                from diffusers import StableDiffusionPipeline
                from transformers import CLIPImageProcessor, CLIPVisionModelWithProjection
                
                model_id = "runwayml/stable-diffusion-v1-5"
                ip_adapter_repo = "h94/IP-Adapter"
                ip_adapter_subfolder = "models"
                ip_adapter_filename = "ip-adapter_sd15.bin"
                
                logger.info(f"Loading IP-Adapter pipeline")
                
                # Load base pipeline
                self._ip_adapter_pipe = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=self.dtype,
                    safety_checker=None,
                    requires_safety_checker=False,
                )
                
                # Load IP-Adapter
                try:
                    # ✅ 优先使用本地IP-Adapter模型
                    from pathlib import Path
                    local_ip_adapter_path = Path(settings.MODELS_PATH) / "models--h94--IP-Adapter" / "snapshots"
                    
                    if local_ip_adapter_path.exists():
                        # 查找最新的快照目录
                        snapshots = list(local_ip_adapter_path.iterdir())
                        if snapshots:
                            latest_snapshot = snapshots[0]
                            
                            # ✅ 使用models子目录（包含ip-adapter权重文件）
                            models_dir = latest_snapshot / "models"
                            
                            if models_dir.exists():
                                logger.info(f"Loading IP-Adapter from local: {models_dir}")
                                logger.info(f"IP-Adapter weight file: {ip_adapter_filename}")
                                
                                # ✅ 从models子目录加载，必须指定subfolder=""
                                self._ip_adapter_pipe.load_ip_adapter(
                                    str(models_dir),
                                    subfolder="",
                                    weight_name=ip_adapter_filename,
                                )
                            else:
                                # models目录不存在，尝试从快照根目录加载（兼容旧结构）
                                logger.info(f"Models dir not found, using snapshot root: {latest_snapshot}")
                                self._ip_adapter_pipe.load_ip_adapter(
                                    str(latest_snapshot),
                                    subfolder="models",
                                    weight_name=ip_adapter_filename,
                                )
                        else:
                            raise FileNotFoundError("No snapshots found")
                    else:
                        # 本地模型不存在，尝试从Hub下载
                        logger.info("Local IP-Adapter not found, trying to load from Hub")
                        self._ip_adapter_pipe.load_ip_adapter(
                            ip_adapter_repo,
                            subfolder=ip_adapter_subfolder,
                            weight_name=ip_adapter_filename,
                        )
                    
                    logger.info("IP-Adapter loaded successfully")
                except Exception as e:
                    logger.error(f"Could not load IP-Adapter weights: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # ✅ 重新抛出异常，不让错误静默
                    raise
                
                self._ip_adapter_pipe = self._ip_adapter_pipe.to(self.device)
                
                if self.device == "cuda":
                    self._ip_adapter_pipe.enable_model_cpu_offload()
                elif self.device == "mps":
                    # ⚠️ 禁用attention slicing，它在MPS上会导致IP-Adapter返回tuple而不是tensor
                    # 这会引发 'tuple' object has no attribute 'shape' 错误
                    logger.info("Attention slicing disabled for MPS (IP-Adapter compatibility)")
                
            except Exception as e:
                logger.error(f"Failed to load IP-Adapter pipeline: {e}")
                raise
        
        return self._ip_adapter_pipe
    
    def preprocess_reference_image(
        self,
        image_path: str,
        target_size: int = 512,
    ) -> Image.Image:
        """
        Preprocess a reference image for IP-Adapter.
        
        Args:
            image_path: Path to reference image
            target_size: Target size for the image
            
        Returns:
            Preprocessed PIL Image
        """
        image = Image.open(image_path).convert("RGB")
        
        # Resize maintaining aspect ratio
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
            pipe = self._get_ip_adapter_pipeline()
            
            # Preprocess reference images
            ref_images = []
            for img_path in reference_images:
                if Path(img_path).exists():
                    img = self.preprocess_reference_image(img_path)
                    ref_images.append(img)
                else:
                    logger.warning(f"Reference image not found: {img_path}")
            
            if not ref_images:
                return {
                    "status": "failed",
                    "error": "No valid reference images provided",
                }
            
            # Set IP-Adapter scale
            try:
                pipe.set_ip_adapter_scale(ip_adapter_scale)
            except Exception as e:
                logger.warning(f"Could not set IP-Adapter scale: {e}")
            
            # Set generator for reproducibility
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)
            
            logger.info(f"Generating with IP-Adapter: {prompt[:50]}...")
            logger.info(f"Using {len(ref_images)} reference images")
            
            # Generate image with IP-Adapter
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
            
            # Convert to bytes
            import io
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            logger.info("IP-Adapter generation successful")
            
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
                    "seed": seed,
                },
            }
            
        except Exception as e:
            logger.error(f"IP-Adapter generation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }
    
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
        This provides the best character consistency results.
        
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
            pipe = self._get_ip_adapter_pipeline()
            
            # Load LoRA if provided
            if lora_path and Path(lora_path).exists():
                try:
                    pipe.load_lora_weights(lora_path)
                    pipe.fuse_lora(lora_scale=lora_weight)
                    logger.info(f"Loaded LoRA: {lora_path} with weight {lora_weight}")
                except Exception as e:
                    logger.warning(f"Failed to load LoRA: {e}")
            
            # Preprocess reference images
            ref_images = []
            for img_path in reference_images:
                if Path(img_path).exists():
                    img = self.preprocess_reference_image(img_path)
                    ref_images.append(img)
            
            if not ref_images:
                return {
                    "status": "failed",
                    "error": "No valid reference images provided",
                }
            
            # Set IP-Adapter scale
            try:
                pipe.set_ip_adapter_scale(ip_adapter_scale)
            except Exception as e:
                logger.warning(f"Failed to set IP-Adapter scale: {e}")
            
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)
            
            logger.info(f"Generating with LoRA + IP-Adapter: {prompt[:50]}...")
            
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
            
            import io
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Unload LoRA
            if lora_path and Path(lora_path).exists():
                try:
                    pipe.unfuse_lora()
                    pipe.unload_lora_weights()
                except Exception as e:
                    logger.warning(f"Failed to unload LoRA weights: {e}")
            
            logger.info("LoRA + IP-Adapter generation successful")
            
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
                    "lora_weight": lora_weight,
                    "seed": seed,
                },
            }
            
        except Exception as e:
            logger.error(f"LoRA + IP-Adapter generation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }
    
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
