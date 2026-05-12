"""
Stable Diffusion Image Generation Service

Generates test images using Stable Diffusion API for quality assessment.
Supports both AUTOMATIC1111 WebUI and ComfyUI backends.
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
import base64
import io
import json
import httpx
from PIL import Image
from app.utils.logger import logger
from app.config.settings import settings


class SDImageGenerator:
    """
    Service for generating images using Stable Diffusion.
    
    Supports:
    - AUTOMATIC1111 WebUI API
    - ComfyUI API
    - Fallback to mock generation
    """
    
    def __init__(self):
        """Initialize SD image generator."""
        # AUTOMATIC1111 WebUI API
        self.webui_url = getattr(settings, 'SD_WEBUI_URL', 'http://127.0.0.1:7860')
        self.webui_enabled = False
        
        # ComfyUI API
        self.comfyui_url = getattr(settings, 'COMFYUI_URL', 'http://127.0.0.1:8188')
        self.comfyui_enabled = False
        
        # Check availability
        self._check_backends()
    
    def _check_backends(self):
        """Check which SD backends are available."""
        try:
            # Check AUTOMATIC1111 WebUI
            response = httpx.get(f"{self.webui_url}/sdapi/v1/cmd-flags", timeout=5.0)
            if response.status_code == 200:
                self.webui_enabled = True
                logger.info(f"AUTOMATIC1111 WebUI available at {self.webui_url}")
        except Exception as e:
            logger.debug(f"WebUI not available: {e}")
        
        try:
            # Check ComfyUI
            response = httpx.get(f"{self.comfyui_url}/system_stats", timeout=5.0)
            if response.status_code == 200:
                self.comfyui_enabled = True
                logger.info(f"ComfyUI available at {self.comfyui_url}")
        except Exception as e:
            logger.debug(f"ComfyUI not available: {e}")
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        lora_path: Optional[str] = None,
        lora_weight: float = 0.8,
        seed: int = 42,
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a single image using Stable Diffusion.
        
        Args:
            prompt: Positive prompt
            negative_prompt: Negative prompt
            lora_path: Path to LoRA model file
            lora_weight: LoRA weight (0.0-1.0)
            seed: Random seed
            width: Image width
            height: Image height
            steps: Sampling steps
            cfg_scale: CFG scale
            output_path: Path to save the generated image
            
        Returns:
            Generation result with image path and metadata
        """
        logger.info(f"Generating image: {prompt[:50]}...")
        
        # Add LoRA to prompt if provided
        if lora_path and Path(lora_path).exists():
            lora_name = Path(lora_path).stem
            prompt = f"<lora:{lora_name}:{lora_weight}>, {prompt}"
            logger.info(f"Added LoRA to prompt: {lora_name} (weight: {lora_weight})")
        
        result = {
            "success": False,
            "image_path": None,
            "seed": seed,
            "backend": None,
            "error": None,
        }
        
        try:
            # Try AUTOMATIC1111 WebUI first
            if self.webui_enabled:
                result = await self._generate_with_webui(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    seed=seed,
                    width=width,
                    height=height,
                    steps=steps,
                    cfg_scale=cfg_scale,
                    output_path=output_path,
                )
                result["backend"] = "webui"
            
            # Try ComfyUI if WebUI failed
            if not result["success"] and self.comfyui_enabled:
                result = await self._generate_with_comfyui(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    seed=seed,
                    width=width,
                    height=height,
                    steps=steps,
                    cfg_scale=cfg_scale,
                    output_path=output_path,
                )
                result["backend"] = "comfyui"
            
            # Fallback to mock generation
            if not result["success"]:
                logger.warning("No SD backend available, using mock generation")
                result = await self._generate_mock_image(
                    prompt=prompt,
                    output_path=output_path,
                )
                result["backend"] = "mock"
            
            return result
        
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            result["error"] = str(e)
            return result
    
    async def _generate_with_webui(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        output_path: Optional[str],
    ) -> Dict[str, Any]:
        """Generate image using AUTOMATIC1111 WebUI API."""
        
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": "DPM++ 2M Karras",
            "scheduler": "karras",
        }
        
        logger.info(f"Calling WebUI API: {self.webui_url}/sdapi/v1/txt2img")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.webui_url}/sdapi/v1/txt2img",
                json=payload,
            )
            
            if response.status_code != 200:
                logger.error(f"WebUI API error: {response.status_code}")
                return {"success": False, "error": f"API error: {response.status_code}"}
            
            data = response.json()
            
            if not data.get("images"):
                return {"success": False, "error": "No images returned"}
            
            # Decode base64 image
            image_data = base64.b64decode(data["images"][0])
            
            # Save image
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(image_data)
                logger.info(f"Saved image to: {output_path}")
            
            return {
                "success": True,
                "image_path": output_path,
                "seed": data.get("seed", seed),
            }
    
    async def _generate_with_comfyui(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        output_path: Optional[str],
    ) -> Dict[str, Any]:
        """Generate image using ComfyUI API."""
        
        # ComfyUI workflow (simplified)
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]}
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt, "clip": ["4", 1]}
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"images": ["8", 0], "filename_prefix": "test_"}
            }
        }
        
        logger.info(f"Calling ComfyUI API: {self.comfyui_url}/prompt")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Queue prompt
            response = await client.post(
                f"{self.comfyui_url}/prompt",
                json={"prompt": workflow},
            )
            
            if response.status_code != 200:
                logger.error(f"ComfyUI API error: {response.status_code}")
                return {"success": False, "error": f"API error: {response.status_code}"}
            
            prompt_id = response.json().get("prompt_id")
            if not prompt_id:
                return {"success": False, "error": "No prompt_id returned"}
            
            # Wait for completion
            await self._wait_for_comfyui_completion(prompt_id)
            
            # Get history
            history_response = await client.get(
                f"{self.comfyui_url}/history/{prompt_id}"
            )
            
            if history_response.status_code != 200:
                return {"success": False, "error": "Failed to get history"}
            
            history = history_response.json()
            if prompt_id not in history:
                return {"success": False, "error": "Prompt not in history"}
            
            # Get output images
            outputs = history[prompt_id].get("outputs", {})
            if not outputs:
                return {"success": False, "error": "No outputs"}
            
            # Find saved image
            for node_id, output in outputs.items():
                if "images" in output and output["images"]:
                    image_info = output["images"][0]
                    # Image is saved by ComfyUI, return path
                    if output_path:
                        # Move or copy the image
                        comfyui_output = Path(settings.STORAGE_PATH) / "output" / image_info["filename"]
                        if comfyui_output.exists():
                            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                            import shutil
                            shutil.copy2(comfyui_output, output_path)
                    
                    return {
                        "success": True,
                        "image_path": output_path,
                        "seed": seed,
                    }
            
            return {"success": False, "error": "No image found in outputs"}
    
    async def _wait_for_comfyui_completion(self, prompt_id: str, timeout: int = 120):
        """Wait for ComfyUI prompt to complete."""
        import asyncio
        
        start_time = asyncio.get_event_loop().time()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            while asyncio.get_event_loop().time() - start_time < timeout:
                response = await client.get(
                    f"{self.comfyui_url}/history/{prompt_id}"
                )
                
                if response.status_code == 200:
                    history = response.json()
                    if prompt_id in history:
                        logger.info("ComfyUI generation completed")
                        return
                
                await asyncio.sleep(2)
        
        logger.warning("ComfyUI generation timeout")
    
    async def _generate_mock_image(
        self,
        prompt: str,
        output_path: Optional[str],
    ) -> Dict[str, Any]:
        """Generate a mock image for testing."""
        import numpy as np
        
        if not output_path:
            return {"success": False, "error": "No output path provided"}
        
        # Create a more meaningful placeholder
        # Generate gradient based on prompt hash
        prompt_hash = hash(prompt) % 1000
        hue = (prompt_hash % 360) / 360.0
        
        # Create HSL gradient image
        img_array = np.zeros((512, 512, 3), dtype=np.uint8)
        
        # Simple gradient
        for y in range(512):
            for x in range(512):
                h = (hue + (x + y) / 1024.0) % 1.0
                s = 0.7
                l = 0.5 + 0.3 * np.sin(x / 100.0) * np.cos(y / 100.0)
                
                # HSL to RGB conversion
                c = (1 - abs(2 * l - 1)) * s
                x_val = c * (1 - abs((h * 6) % 2 - 1))
                m = l - c / 2
                
                if h < 1/6:
                    r, g, b = c, x_val, 0
                elif h < 2/6:
                    r, g, b = x_val, c, 0
                elif h < 3/6:
                    r, g, b = 0, c, x_val
                elif h < 4/6:
                    r, g, b = 0, x_val, c
                elif h < 5/6:
                    r, g, b = x_val, 0, c
                else:
                    r, g, b = c, 0, x_val
                
                img_array[y, x] = [
                    int((r + m) * 255),
                    int((g + m) * 255),
                    int((b + m) * 255)
                ]
        
        img = Image.fromarray(img_array)
        
        # Save image
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        
        logger.info(f"Saved mock image to: {output_path}")
        
        return {
            "success": True,
            "image_path": output_path,
            "seed": 42,
        }
    
    async def generate_batch(
        self,
        prompts: List[Dict[str, Any]],
        lora_path: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple images.
        
        Args:
            prompts: List of prompt configs
            lora_path: LoRA model path
            output_dir: Output directory
            
        Returns:
            List of generation results
        """
        results = []
        
        for i, prompt_config in enumerate(prompts):
            try:
                output_path = None
                if output_dir:
                    output_path = f"{output_dir}/test_{i+1:02d}.png"
                
                result = await self.generate_image(
                    prompt=prompt_config.get("prompt", ""),
                    negative_prompt=prompt_config.get("negative_prompt", ""),
                    lora_path=lora_path,
                    lora_weight=prompt_config.get("lora_weight", 0.8),
                    seed=prompt_config.get("seed", 42 + i),
                    output_path=output_path,
                )
                
                result["index"] = i + 1
                result["prompt"] = prompt_config.get("prompt", "")
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to generate image {i+1}: {e}")
                results.append({
                    "index": i + 1,
                    "success": False,
                    "error": str(e),
                    "prompt": prompt_config.get("prompt", ""),
                })
        
        return results
