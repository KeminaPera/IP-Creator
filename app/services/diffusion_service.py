"""
Diffusion Service

Handles AI image and video generation using Diffusers library.
Supports Stable Diffusion for images and CogVideoX for video generation.
"""
import io
import torch
from typing import Optional, Dict, Any, List
from pathlib import Path
from PIL import Image
from app.config.settings import settings
from app.utils.logger import logger
from app.services.ip_adapter_service import ip_adapter_service
from app.core.gpu_cache import gpu_cache


class DiffusionService:
    """
    Service for AI image and video generation.
    
    Uses Diffusers library with Stable Diffusion for images
    and CogVideoX/compatible models for video generation.
    """
    
    def __init__(self):
        """Initialize diffusion service."""
        # Use cached GPU info to avoid redundant torch.cuda.is_available() checks
        gpu_info = gpu_cache.get_info()
        self.device = "cuda" if gpu_info["cuda_available"] else "cpu"
        self.dtype = torch.float16 if gpu_info["cuda_available"] else torch.float32
        self._image_pipe = None
        self._video_pipe = None
        self.models_path = Path(settings.MODELS_PATH)
        self.models_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"DiffusionService initialized on {self.device} with {self.dtype}")
    
    def _get_image_pipeline(self):
        """Lazy-load image generation pipeline."""
        if self._image_pipe is None:
            try:
                from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
                
                model_id = "runwayml/stable-diffusion-v1-5"
                logger.info(f"Loading image pipeline: {model_id}")
                
                self._image_pipe = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=self.dtype,
                    safety_checker=None,
                    requires_safety_checker=False,
                )
                
                # Use faster scheduler
                self._image_pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                    self._image_pipe.scheduler.config
                )
                
                self._image_pipe = self._image_pipe.to(self.device)
                
                # Enable memory efficient attention if available
                if hasattr(self._image_pipe, "enable_xformers_memory_efficient_attention"):
                    try:
                        self._image_pipe.enable_xformers_memory_efficient_attention()
                    except Exception as e:
                        logger.warning(f"Failed to enable xformers: {e}")
                
                # Enable CPU offloading for low VRAM
                if self.device == "cuda":
                    self._image_pipe.enable_model_cpu_offload()
                
                logger.info("Image pipeline loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load image pipeline: {e}")
                raise
        
        return self._image_pipe
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 30,
        cfg_scale: float = 7.0,
        seed: Optional[int] = None,
        lora_path: Optional[str] = None,
        lora_weight: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate an image using Stable Diffusion.
        
        Args:
            prompt: Image generation prompt
            negative_prompt: Negative prompt
            width: Image width
            height: Image height
            steps: Sampling steps
            cfg_scale: CFG guidance scale
            seed: Random seed for reproducibility
            lora_path: Path to LoRA weights
            lora_weight: LoRA weight (0.0-1.0)
            
        Returns:
            Dictionary with image bytes and metadata
        """
        try:
            pipe = self._get_image_pipeline()
            
            # Load LoRA if provided
            if lora_path and Path(lora_path).exists():
                try:
                    from diffusers import LoraLoaderMixin
                    pipe.load_lora_weights(lora_path)
                    logger.info(f"Loaded LoRA weights: {lora_path}")
                except Exception as e:
                    logger.warning(f"Failed to load LoRA weights: {e}")
            
            # Set generator for reproducibility
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)
            
            logger.info(f"Generating image: {prompt[:50]}...")
            
            # Generate image
            result = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=cfg_scale,
                generator=generator,
                num_images_per_prompt=1,
            )
            
            image = result.images[0]
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            # Unload LoRA if loaded
            if lora_path and Path(lora_path).exists():
                try:
                    pipe.unload_lora_weights()
                except Exception as e:
                    logger.warning(f"Failed to unload LoRA weights: {e}")
            
            logger.info("Image generated successfully")
            
            return {
                "status": "success",
                "image_bytes": img_byte_arr.getvalue(),
                "parameters": {
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg_scale": cfg_scale,
                    "seed": seed,
                },
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }
    
    async def generate_image_with_ip_adapter(
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
            prompt: Image generation prompt
            reference_images: List of reference image paths
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
        return await ip_adapter_service.generate_with_ip_adapter(
            prompt=prompt,
            reference_images=reference_images,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            ip_adapter_scale=ip_adapter_scale,
            seed=seed,
        )
    
    async def generate_image_with_lora_and_ip(
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
        Generate image with both LoRA and IP-Adapter.
        
        Combines LoRA for style + IP-Adapter for character consistency.
        
        Args:
            prompt: Image generation prompt
            reference_images: List of reference image paths
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
        return await ip_adapter_service.generate_with_lora_and_ip(
            prompt=prompt,
            reference_images=reference_images,
            lora_path=lora_path,
            lora_weight=lora_weight,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            ip_adapter_scale=ip_adapter_scale,
            seed=seed,
        )
    
    async def generate_image_to_video(
        self,
        image_path: str,
        prompt: str = "",
        duration_seconds: int = 5,
        fps: int = 8,
        width: int = 512,
        height: int = 512,
        steps: int = 50,
    ) -> Dict[str, Any]:
        """
        Generate video from image using CogVideoX or similar.
        
        Note: This requires the CogVideoX model which is very large.
        Falls back to simple frame generation if model not available.
        
        Args:
            image_path: Path to starting image
            prompt: Video prompt
            duration_seconds: Video duration
            fps: Frames per second
            width: Video width
            height: Video height
            steps: Sampling steps
            
        Returns:
            Dictionary with video bytes and metadata
        """
        try:
            # Try to use CogVideoX if available
            try:
                return await self._generate_with_cogvideo(
                    image_path, prompt, duration_seconds, fps, width, height, steps
                )
            except Exception as e:
                logger.warning(f"CogVideoX not available, using fallback: {e}")
                return await self._generate_video_fallback(
                    image_path, duration_seconds, fps
                )
                
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
            }
    
    async def _generate_with_cogvideo(
        self,
        image_path: str,
        prompt: str,
        duration_seconds: int,
        fps: int,
        width: int,
        height: int,
        steps: int,
    ) -> Dict[str, Any]:
        """Generate video using CogVideoX."""
        from diffusers import CogVideoXImageToVideoPipeline
        from diffusers.utils import export_to_video
        
        if self._video_pipe is None:
            model_id = "THUDM/CogVideoX-5b-I2V"
            logger.info(f"Loading video pipeline: {model_id}")
            
            self._video_pipe = CogVideoXImageToVideoPipeline.from_pretrained(
                model_id,
                torch_dtype=self.dtype,
            )
            self._video_pipe = self._video_pipe.to(self.device)
            
            if self.device == "cuda":
                self._video_pipe.enable_model_cpu_offload()
        
        # Load image
        image = Image.open(image_path).convert("RGB")
        image = image.resize((width, height))
        
        # Generate video frames
        num_frames = int(duration_seconds * fps)
        
        result = self._video_pipe(
            image=image,
            prompt=prompt,
            num_frames=num_frames,
            num_inference_steps=steps,
            guidance_scale=6.0,
        )
        
        video_frames = result.frames[0]
        
        # Export to video file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            export_to_video(video_frames, tmp.name, fps=fps)
            with open(tmp.name, "rb") as f:
                video_bytes = f.read()
        
        return {
            "status": "success",
            "video_bytes": video_bytes,
            "parameters": {
                "prompt": prompt,
                "duration": duration_seconds,
                "fps": fps,
                "width": width,
                "height": height,
            },
        }
    
    async def _generate_video_fallback(
        self,
        image_path: str,
        duration_seconds: int,
        fps: int,
    ) -> Dict[str, Any]:
        """
        Fallback video generation using image animation.
        Creates a simple zoom/pan effect on the image.
        """
        import numpy as np
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available for video generation fallback")
            return {
                "status": "failed",
                "error": "Video generation requires CogVideoX or OpenCV",
            }
        
        # Load image
        image = Image.open(image_path).convert("RGB")
        
        # Calculate frames
        num_frames = int(duration_seconds * fps)
        
        # Create zoom effect
        frames = []
        for i in range(num_frames):
            progress = i / num_frames
            # Subtle zoom from 1.0 to 1.1
            scale = 1.0 + (progress * 0.1)
            
            w, h = image.size
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Crop center
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            cropped = resized.crop((left, top, left + w, top + h))
            
            frames.append(np.array(cropped))
        
        # Write video
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(tmp.name, fourcc, fps, (w, h))
            
            for frame in frames:
                out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            
            out.release()
            
            with open(tmp.name, "rb") as f:
                video_bytes = f.read()
        
        return {
            "status": "success",
            "video_bytes": video_bytes,
            "parameters": {
                "duration": duration_seconds,
                "fps": fps,
                "frames": num_frames,
                "note": "Fallback mode - simple animation",
            },
        }


# Global diffusion service instance
diffusion_service = DiffusionService()
