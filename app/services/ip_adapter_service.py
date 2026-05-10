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
import torch
from typing import Optional, Dict, Any, List
from pathlib import Path
from PIL import Image
from app.config.settings import settings
from app.utils.logger import logger
from app.core.gpu_cache import gpu_cache


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
        self.device = "cuda" if gpu_info["cuda_available"] else "cpu"
        self.dtype = torch.float16 if gpu_info["cuda_available"] else torch.float32
        self._ip_adapter_pipe = None
        self._image_encoder = None
        self.models_path = Path(settings.MODELS_PATH)
        
        logger.info(f"IPAdapterService initialized on {self.device}")
    
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
                    self._ip_adapter_pipe.load_ip_adapter(
                        ip_adapter_repo,
                        subfolder=ip_adapter_subfolder,
                        weight_name=ip_adapter_filename,
                    )
                    logger.info("IP-Adapter loaded successfully")
                except Exception as e:
                    logger.warning(f"Could not load IP-Adapter weights: {e}")
                    logger.info("Falling back to standard generation without IP-Adapter")
                
                self._ip_adapter_pipe = self._ip_adapter_pipe.to(self.device)
                
                if self.device == "cuda":
                    self._ip_adapter_pipe.enable_model_cpu_offload()
                
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
            except:
                logger.warning("Could not set IP-Adapter scale")
            
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
                    logger.info(f"Loaded LoRA: {lora_path}")
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
            except:
                pass
            
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
                    pipe.unload_lora_weights()
                except:
                    pass
            
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


# Global IP-Adapter service instance
ip_adapter_service = IPAdapterService()
