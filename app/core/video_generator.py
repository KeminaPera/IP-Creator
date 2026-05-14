"""
Video Generator Module

Orchestrates AI content generation including story creation,
image generation, and video generation with Diffusers.
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
from app.core.llm_manager import llm_manager
from app.config.settings import settings
from app.utils.logger import logger
from app.services.diffusion_service import diffusion_service
from app.services.storage_service import storage_service


class VideoGenerator:
    """
    Service for AI-powered content generation.
    
    Handles story/script generation using LLMs, image generation
    with LoRA constraints, and video generation with Diffusers models.
    """
    
    def __init__(self):
        """Initialize video generator."""
        self.videos_path = Path(settings.VIDEOS_PATH)
        self.videos_path.mkdir(parents=True, exist_ok=True)
    
    async def generate_story(
        self,
        prompt: str,
        ip_name: Optional[str] = None,
        style: Optional[str] = None,
        duration_seconds: int = 10,
        channel_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate story and storyboard using LLM.
        
        Args:
            prompt: Story prompt or theme
            ip_name: IP character name to include
            style: Story style (healing, comedy, adventure, etc.)
            duration_seconds: Target video duration
            
        Returns:
            Generated story with scenes and prompts
        """
        try:
            from pathlib import Path
            from datetime import datetime
            import json
            
            # Build prompt for story generation
            system_prompt = """You are a professional scriptwriter for short AI-generated videos.
Create a healing, heartwarming story suitable for a short video.
Return the response in JSON format with the following structure:
{
  "title": "Story title",
  "description": "Brief story description",
  "scenes": [
    {
      "scene_number": 1,
      "description": "Scene description",
      "prompt": "Detailed image generation prompt",
      "duration": 3
    }
  ]
}"""
            
            user_prompt = f"Create a {duration_seconds}-second {style or 'healing'} story"
            if ip_name:
                user_prompt += f" featuring the character '{ip_name}'"
            user_prompt += f". Theme: {prompt}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            # Call LLM
            story_text = await llm_manager.chat_completion(
                messages=messages,
                temperature=0.8,
                max_tokens=2048,
                model_id=channel_id,
            )
            
            logger.info(f"Generated story: {story_text[:100]}...")
            
            # Clean Markdown code block markers if present
            # LLM often wraps JSON in ```json ... ``` blocks
            if story_text.startswith('```'):
                # Remove opening ```json or ```
                lines = story_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]  # Remove first line
                # Remove closing ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                story_text = '\n'.join(lines)
                logger.info(f"Cleaned Markdown markers from story")
            
            # Try to parse title and description from LLM response
            title = ""
            description = ""
            try:
                # Try to parse as JSON first
                story_data = json.loads(story_text)
                title = story_data.get('title', '')
                description = story_data.get('description', '')
            except json.JSONDecodeError as e:
                # If not JSON, use default values
                logger.debug(f"Story text is not JSON: {e}")
            
            # Generate title if empty
            if not title:
                title = f"Story - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Save story to file
            story_dir = Path('./data/stories')
            story_dir.mkdir(parents=True, exist_ok=True)
            
            # Create story content
            story_content = {
                'title': title,
                'description': description,
                'story': story_text,
                'prompt': prompt,
                'ip_name': ip_name,
                'style': style,
                'duration_seconds': duration_seconds,
                'generated_at': datetime.now().isoformat()
            }
            
            # Save to JSON file
            file_path = story_dir / f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(story_content, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Story saved to: {file_path}")
            
            return {
                "story": story_text,
                "title": title,
                "description": description,
                "file_path": str(file_path),
                "word_count": len(story_text),
                "status": "success",
            }
        
        except Exception as e:
            logger.error(f"Story generation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def generate_image(
        self,
        prompt: str,
        ip_asset_id: int = 0,
        channel_id: Optional[int] = None,
        lora_path: Optional[str] = None,
        reference_images: Optional[List[str]] = None,
        width: int = 512,
        height: int = 512,
        steps: int = 30,
        cfg_scale: float = 7.0,
        lora_weight: float = 0.7,
        use_ip_adapter: bool = False,
        ip_adapter_scale: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate image with LoRA and optional IP constraints using Diffusers.
        
        Args:
            prompt: Image generation prompt
            ip_asset_id: Associated IP asset ID for file storage
            channel_id: LLM channel ID for model routing (if using API-based image generation)
            lora_path: Path to LoRA model
            reference_images: List of reference image paths for IP-Adapter
            width: Image width
            height: Image height
            steps: Sampling steps
            cfg_scale: CFG guidance scale
            lora_weight: LoRA model weight
            use_ip_adapter: Whether to use IP-Adapter for consistency
            ip_adapter_scale: IP-Adapter weight
            
        Returns:
            Generated image path and metadata
        """
        try:
            logger.info(f"Generating image: {prompt[:50]}...")
            logger.info(f"Channel ID: {channel_id}, LoRA: {lora_path}, Weight: {lora_weight}")
            logger.info(f"IP-Adapter: {use_ip_adapter}, Ref images: {reference_images}")
            
            # If channel_id is provided, use API-based generation
            if channel_id:
                from app.services.cloud_gen_service import CloudGenService
                from app.config.database import async_session_factory
                from app.models.llm_model import LLMConfig
                from sqlalchemy import select
                            
                logger.info(f"Using API-based image generation with channel_id={channel_id}")
                            
                # Get channel info from database
                async with async_session_factory() as db:
                    result_db = await db.execute(
                        select(LLMConfig).where(LLMConfig.id == channel_id)
                    )
                    channel = result_db.scalar_one_or_none()
                
                if not channel:
                    return {"status": "failed", "error": f"Channel {channel_id} not found"}
                
                if not channel.is_active:
                    return {"status": "failed", "error": f"Channel {channel_id} is not active"}
                
                # Decrypt API key
                from app.security.crypto import encryption_service
                api_key = encryption_service.decrypt(channel.api_key_encrypted) if channel.api_key_encrypted else ""
                
                # Call cloud generation service
                cloud_service = CloudGenService()
                result = await cloud_service.generate_image(
                    provider=channel.provider,
                    model_name=channel.model_name,
                    prompt=prompt,
                    api_key=api_key,
                    api_endpoint=channel.api_endpoint,
                    width=width,
                    height=height,
                    channel_id=channel_id,  # Pass channel_id for health metrics update
                )
                
                if result["status"] == "failed":
                    return result
            else:
                # Use local diffusion model (original logic)
                logger.info("Using local diffusion model for image generation")
                
                # Choose generation method based on parameters
                if use_ip_adapter and reference_images:
                    if lora_path:
                        # Use both LoRA + IP-Adapter for best results
                        result = await diffusion_service.generate_image_with_lora_and_ip(
                            prompt=prompt,
                            reference_images=reference_images,
                            lora_path=lora_path,
                            lora_weight=lora_weight,
                            width=width,
                            height=height,
                            steps=steps,
                            cfg_scale=cfg_scale,
                            ip_adapter_scale=ip_adapter_scale,
                        )
                    else:
                        # Use IP-Adapter only
                        result = await diffusion_service.generate_image_with_ip_adapter(
                            prompt=prompt,
                            reference_images=reference_images,
                            width=width,
                            height=height,
                            steps=steps,
                            cfg_scale=cfg_scale,
                            ip_adapter_scale=ip_adapter_scale,
                        )
                else:
                    # Standard generation with optional LoRA
                    result = await diffusion_service.generate_image(
                        prompt=prompt,
                        width=width,
                        height=height,
                        steps=steps,
                        cfg_scale=cfg_scale,
                        lora_path=lora_path,
                        lora_weight=lora_weight,
                    )
            
            if result["status"] == "failed":
                return result
            
            # Save generated image
            image_bytes = result["image_bytes"]
            file_path, file_url = await storage_service.save_generated_image(
                image_data=image_bytes,
                ip_asset_id=ip_asset_id,
            )
            
            return {
                "status": "success",
                "file_path": file_path,  # Use file_path for consistency with create_content_record
                "image_path": file_path,  # Keep for backward compatibility
                "image_url": file_url,
                "file_size": len(image_bytes),  # Add file size for content library display
                "parameters": result.get("parameters", {}),  # Safe access, default to empty dict
            }
        
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def generate_video(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        ip_asset_id: int = 0,
        channel_id: Optional[int] = None,
        duration_seconds: int = 5,
        fps: int = 24,
        width: int = 512,
        height: int = 512,
        steps: int = 50,
        cfg_scale: float = 7.0,
        use_ip_adapter: bool = False,
        reference_images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate video using Diffusers I2V pipeline.
        
        Args:
            prompt: Video generation prompt
            image_path: Starting image for image-to-video
            ip_asset_id: Associated IP asset ID for file storage
            channel_id: LLM channel ID for model routing (if using API-based video generation)
            duration_seconds: Video duration
            fps: Frames per second
            width: Video width
            height: Video height
            steps: Sampling steps
            cfg_scale: CFG guidance scale
            use_ip_adapter: Whether to use IP-Adapter for consistency
            reference_images: List of reference image paths for IP-Adapter
            
        Returns:
            Generated video path and metadata
        """
        try:
            logger.info(f"Generating video: {prompt[:50]}...")
            logger.info(f"Duration: {duration_seconds}s, FPS: {fps}")
            
            if not image_path or not Path(image_path).exists():
                return {
                    "status": "failed",
                    "error": "Starting image is required for video generation",
                }
            
            # Call diffusion service for video generation
            result = await diffusion_service.generate_image_to_video(
                image_path=image_path,
                prompt=prompt,
                duration_seconds=duration_seconds,
                fps=fps,
                width=width,
                height=height,
                steps=steps,
            )
            
            if result["status"] == "failed":
                return result
            
            # Save generated video
            video_bytes = result["video_bytes"]
            file_path, file_url = await storage_service.save_generated_video(
                video_data=video_bytes,
                ip_asset_id=ip_asset_id,
            )
            
            return {
                "status": "success",
                "video_path": file_path,
                "video_url": file_url,
                "parameters": result["parameters"],
            }
        
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return {"status": "failed", "error": str(e)}


# Global video generator instance
video_generator = VideoGenerator()
