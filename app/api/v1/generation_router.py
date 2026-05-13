"""  
Generation Router

API endpoints for content generation (story, image, video).
"""
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from app.config.database import get_db_session
from app.core.video_generator import video_generator
from app.core.generation_dispatcher import generation_dispatcher
from app.services.adapters.protocol import GenerationRequest, GenerationCapability
from app.api.deps import get_current_user
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    AppException
)
from app.utils.response import success_response, list_response, created_response, updated_response, deleted_response, message_response
from app.utils.logger import logger
from app.services.storage_service import storage_service
from app.services.ip_adapter_service import ip_adapter_service
from app.models.ip_asset import IPAsset
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/generate", tags=["Generation"])


# Request schemas
class StoryGenerationRequest(BaseModel):
    """Request model for story generation."""
    prompt: str = Field(..., description="Story prompt or theme")
    ip_name: Optional[str] = Field(None, description="IP character name")
    ip_asset_id: Optional[int] = Field(None, description="Associated IP asset ID")
    style: Optional[str] = Field(None, description="Story style (healing, comedy, etc.)")
    duration_seconds: int = Field(default=10, ge=5, le=60, description="Target duration")
    channel_id: Optional[int] = Field(None, description="LLM channel ID (from llm_configs) for dispatcher routing")


class ImageGenerationRequest(BaseModel):
    """Request model for image generation."""
    prompt: str = Field(..., description="Image generation prompt")
    ip_asset_id: int = Field(default=0, description="Associated IP asset ID")
    lora_path: Optional[str] = Field(None, description="Path to LoRA model")
    reference_images: Optional[List[str]] = Field(None, description="Reference image paths for IP-Adapter")
    width: int = Field(default=512, ge=256, le=2048)
    height: int = Field(default=512, ge=256, le=2048)
    steps: int = Field(default=30, ge=10, le=100)
    cfg_scale: float = Field(default=7.0, ge=1.0, le=20.0)
    lora_weight: float = Field(default=0.7, ge=0.0, le=1.0)
    use_ip_adapter: bool = Field(default=False, description="Use IP-Adapter for consistency")
    ip_adapter_scale: float = Field(default=0.7, ge=0.0, le=1.0)
    channel_id: Optional[int] = Field(None, description="LLM channel ID for dispatcher routing")


class VideoGenerationRequest(BaseModel):
    """Request model for video generation."""
    prompt: str = Field(..., description="Video generation prompt")
    image_path: Optional[str] = Field(None, description="Starting image for image-to-video")
    ip_asset_id: int = Field(default=0, description="Associated IP asset ID")
    duration_seconds: int = Field(default=5, ge=1, le=30)
    fps: int = Field(default=24, ge=12, le=60)
    width: int = Field(default=512, ge=256, le=2048)
    height: int = Field(default=512, ge=256, le=2048)
    steps: int = Field(default=50, ge=10, le=100)
    cfg_scale: float = Field(default=7.0, ge=1.0, le=20.0)
    use_ip_adapter: bool = Field(default=False, description="Use IP-Adapter for consistency")
    reference_images: Optional[List[str]] = Field(None, description="Reference image paths for IP-Adapter")
    channel_id: Optional[int] = Field(None, description="LLM channel ID for dispatcher routing")


@router.post("/story")
async def generate_story(
    request: StoryGenerationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate story/script using LLM.
    
    If channel_id is provided, routes through the generation dispatcher
    (ComfyUI-style adapter architecture). Otherwise, falls back to the
    legacy video_generator for backward compatibility.
    """
    try:
        logger.info(f"Story generation request from user {current_user['username']}")
        logger.info(f"Prompt: {request.prompt}, IP: {request.ip_name}, Channel: {request.channel_id}")
        
        # New adapter-based dispatch path
        if request.channel_id:
            gen_request = GenerationRequest(
                prompt=request.prompt,
                generation_type="text",
                channel_id=request.channel_id,
                ip_asset_id=request.ip_asset_id,
                ip_name=request.ip_name,
                style=request.style,
                parameters={
                    "text_type": "story",
                    "duration_seconds": request.duration_seconds,
                    "style": request.style,
                },
            )
            response = await generation_dispatcher.dispatch(gen_request)
            
            if response.status == "failed":
                raise AppException(
                    status_code=500,
                    error="GenerationError",
                    message=response.error or "Story generation failed"
                )
            
            return created_response(
                data={
                    "story": response.content,
                    "status": "success",
                    "metadata": response.metadata,
                },
                message="Story generated successfully"
            )
        
        # Legacy fallback path
        result = await video_generator.generate_story(
            prompt=request.prompt,
            ip_name=request.ip_name,
            style=request.style,
            duration_seconds=request.duration_seconds,
        )
        
        if result.get("status") == "failed":
            raise AppException(
                status_code=500,
                error="GenerationError",
                message=result.get("error", "Story generation failed")
            )
        
        return created_response(
            data=result,
            message="Story generated successfully"
        )
    
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Story generation error: {e}")
        raise AppException(
            status_code=500,
            error="GenerationError",
            message="Story generation failed"
        )


@router.post("/image")
async def generate_image(
    request: ImageGenerationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate image with LoRA and IP constraints.
    
    If channel_id is provided, routes through the generation dispatcher.
    Otherwise, falls back to the legacy video_generator.
    """
    try:
        logger.info(f"Image generation request from user {current_user['username']}")
        logger.info(f"Prompt: {request.prompt}, Channel: {request.channel_id}")
        
        # New adapter-based dispatch path
        if request.channel_id:
            gen_request = GenerationRequest(
                prompt=request.prompt,
                generation_type="image",
                channel_id=request.channel_id,
                ip_asset_id=request.ip_asset_id,
                parameters={
                    "width": request.width,
                    "height": request.height,
                    "steps": request.steps,
                    "cfg_scale": request.cfg_scale,
                    "lora_path": request.lora_path,
                    "lora_weight": request.lora_weight,
                    "use_ip_adapter": request.use_ip_adapter,
                    "ip_adapter_scale": request.ip_adapter_scale,
                    "reference_images": request.reference_images,
                },
            )
            response = await generation_dispatcher.dispatch(gen_request)
            
            if response.status == "failed":
                raise AppException(
                    status_code=500,
                    error="GenerationError",
                    message=response.error or "Image generation failed"
                )
            
            return created_response(
                data={
                    "image_path": response.output_path,
                    "image_url": response.output_url,
                    "parameters": response.metadata.get("parameters", {}),
                    "metadata": response.metadata,
                },
                message="Image generated successfully"
            )
        
        # Legacy fallback path
        result = await video_generator.generate_image(
            prompt=request.prompt,
            ip_asset_id=request.ip_asset_id,
            lora_path=request.lora_path,
            reference_images=request.reference_images,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
            lora_weight=request.lora_weight,
            use_ip_adapter=request.use_ip_adapter,
            ip_adapter_scale=request.ip_adapter_scale,
        )
        
        if result.get("status") == "failed":
            raise AppException(
                status_code=500,
                error="GenerationError",
                message=result.get("error", "Image generation failed")
            )
        
        return created_response(
            data=result,
            message="Image generated successfully"
        )
    
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Image generation error: {e}")
        raise AppException(
            status_code=500,
            error="GenerationError",
            message="Image generation failed"
        )


@router.post("/video")
async def generate_video(
    request: VideoGenerationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate video using DiT architecture.
    
    If channel_id is provided, routes through the generation dispatcher.
    Otherwise, falls back to the legacy video_generator.
    """
    try:
        logger.info(f"Video generation request from user {current_user['username']}")
        logger.info(f"Prompt: {request.prompt}, Duration: {request.duration_seconds}s, Channel: {request.channel_id}")
        
        # New adapter-based dispatch path
        if request.channel_id:
            gen_request = GenerationRequest(
                prompt=request.prompt,
                generation_type="video",
                channel_id=request.channel_id,
                ip_asset_id=request.ip_asset_id,
                parameters={
                    "image_path": request.image_path,
                    "duration_seconds": request.duration_seconds,
                    "fps": request.fps,
                    "width": request.width,
                    "height": request.height,
                    "steps": request.steps,
                    "cfg_scale": request.cfg_scale,
                },
            )
            response = await generation_dispatcher.dispatch(gen_request)
            
            if response.status == "failed":
                raise AppException(
                    status_code=500,
                    error="GenerationError",
                    message=response.error or "Video generation failed"
                )
            
            return created_response(
                data={
                    "video_path": response.output_path,
                    "video_url": response.output_url,
                    "parameters": response.metadata.get("parameters", {}),
                    "metadata": response.metadata,
                },
                message="Video generated successfully"
            )
        
        # Legacy fallback path
        result = await video_generator.generate_video(
            prompt=request.prompt,
            image_path=request.image_path,
            ip_asset_id=request.ip_asset_id,
            duration_seconds=request.duration_seconds,
            fps=request.fps,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
        )
        
        if result.get("status") == "failed":
            raise AppException(
                status_code=500,
                error="GenerationError",
                message=result.get("error", "Video generation failed")
            )
        
        return created_response(
            data=result,
            message="Video generated successfully"
        )
    
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        raise AppException(
            status_code=500,
            error="GenerationError",
            message="Video generation failed"
        )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    directory: str = "ip_assets",
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a file for use in generation.
    
    Supports reference images, LoRA models, etc.
    """
    try:
        file_path, file_url = await storage_service.save_upload_file(
            upload_file=file,
            directory=directory,
        )
        
        return created_response(
            data={
                "file_path": file_path,
                "file_url": file_url,
                "filename": file.filename,
            },
            message="File uploaded successfully"
        )
    
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise AppException(
            status_code=500,
            error="UploadError",
            message="File upload failed"
        )


@router.get("/files/{directory}/{filename}")
async def get_file(
    directory: str,
    filename: str,
):
    """
    Serve a stored file (image, video, etc.).
    """
    try:
        file_path = storage_service.get_file_path(directory, filename)
        
        if not file_path:
            raise NotFoundException(message="File not found")
        
        return FileResponse(str(file_path))
    
    except AppException:
        raise
    except Exception as e:
        logger.error(f"File serving error: {e}")
        raise AppException(
            status_code=500,
            error="FileError",
            message="Failed to serve file"
        )


@router.post("/story/async")
async def generate_story_async(
    request: StoryGenerationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create async story generation task.
    
    Returns task ID for monitoring via /tasks/list endpoint.
    """
    try:
        from celery_worker import generate_story_task
        
        # Create Celery task using apply_async (more reliable than send_task)
        task = generate_story_task.apply_async(
            args=[
                request.prompt,
                request.ip_name,
                request.ip_asset_id,
                request.style,
                request.duration_seconds,
                request.channel_id,
            ],
            queue='story_generation'
        )
        
        # Create task record in database with explicit local time
        from app.models.task import TaskRecord
        
        task_record = TaskRecord(
            task_id=task.id,
            task_type="story_generation",
            ip_asset_id=request.ip_asset_id,
            channel_id=request.channel_id,
            status="pending",
            parameters={
                "prompt": request.prompt,
                "ip_name": request.ip_name,
                "style": request.style,
                "duration_seconds": request.duration_seconds,
                "channel_id": request.channel_id,
            },
            created_by=current_user["id"] if current_user.get("id") else 1,
            created_at=datetime.now(),  # Use local time to match started_at
        )
        
        db.add(task_record)
        await db.commit()
        await db.refresh(task_record)
        
        return created_response(
            data={
                "task_id": task.id,
                "task_type": "story_generation",
                "status": "pending",
            },
            message="Story generation task created successfully"
        )
    
    except Exception as e:
        logger.error(f"Async story generation error: {e}")
        raise AppException(
            status_code=500,
            error="TaskCreationError",
            message="Failed to create async story task"
        )


@router.post("/image/async")
async def generate_image_async(
    request: ImageGenerationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create async image generation task.
    
    Returns task ID for monitoring via /tasks/list endpoint.
    """
    try:
        from celery_worker import generate_image_task
        
        # Create Celery task using apply_async (more reliable than send_task)
        task = generate_image_task.apply_async(
            args=[
                request.prompt,
                request.ip_asset_id,
            ],
            kwargs={
                "channel_id": request.channel_id,
                "lora_path": request.lora_path,
                "reference_images": request.reference_images or [],
                "width": request.width,
                "height": request.height,
                "steps": request.steps,
                "cfg_scale": request.cfg_scale,
                "lora_weight": request.lora_weight,
                "use_ip_adapter": request.use_ip_adapter,
                "ip_adapter_scale": request.ip_adapter_scale,
            }
        )
        
        # Create task record in database with explicit local time
        from app.models.task import TaskRecord
        
        task_record = TaskRecord(
            task_id=task.id,
            task_type="image_generation",
            ip_asset_id=request.ip_asset_id,
            channel_id=request.channel_id,
            status="pending",
            parameters={
                "prompt": request.prompt,
                "ip_asset_id": request.ip_asset_id,
                "channel_id": request.channel_id,
                "lora_path": request.lora_path,
                "reference_images": request.reference_images or [],
                "width": request.width,
                "height": request.height,
                "steps": request.steps,
                "cfg_scale": request.cfg_scale,
                "lora_weight": request.lora_weight,
                "use_ip_adapter": request.use_ip_adapter,
                "ip_adapter_scale": request.ip_adapter_scale,
            },
            created_by=current_user["id"] if current_user.get("id") else 1,
            created_at=datetime.now(),  # Use local time to match started_at
        )
        
        db.add(task_record)
        await db.commit()
        await db.refresh(task_record)
        
        return created_response(
            data={
                "task_id": task.id,
                "task_type": "image_generation",
                "status": "pending",
            },
            message="Image generation task created successfully"
        )
    
    except Exception as e:
        logger.error(f"Async image generation error: {e}")
        raise AppException(
            status_code=500,
            error="TaskCreationError",
            message="Failed to create async image task"
        )


@router.post("/video/async")
async def generate_video_async(
    request: VideoGenerationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create async video generation task.
    
    Returns task ID for monitoring via /tasks/list endpoint.
    """
    try:
        from celery_worker import generate_video_task
        
        # Create Celery task using apply_async (more reliable than send_task)
        task = generate_video_task.apply_async(
            args=[
                request.prompt,
                request.image_path,
                request.ip_asset_id,
            ],
            kwargs={
                "channel_id": request.channel_id,
                "duration_seconds": request.duration_seconds,
                "fps": request.fps,
                "width": request.width,
                "height": request.height,
                "steps": request.steps,
                "cfg_scale": request.cfg_scale,
                "use_ip_adapter": request.use_ip_adapter,
                "reference_images": request.reference_images or [],
            }
        )
        
        # Create task record in database with explicit local time
        from app.models.task import TaskRecord
        
        task_record = TaskRecord(
            task_id=task.id,
            task_type="video_generation",
            ip_asset_id=request.ip_asset_id,
            channel_id=request.channel_id,
            status="pending",
            parameters={
                "prompt": request.prompt,
                "image_path": request.image_path,
                "ip_asset_id": request.ip_asset_id,
                "channel_id": request.channel_id,
                "duration_seconds": request.duration_seconds,
                "fps": request.fps,
                "width": request.width,
                "height": request.height,
                "steps": request.steps,
                "cfg_scale": request.cfg_scale,
                "use_ip_adapter": request.use_ip_adapter,
                "reference_images": request.reference_images or [],
            },
            created_by=current_user["id"] if current_user.get("id") else 1,
            created_at=datetime.now(),  # Use local time to match started_at
        )
        
        db.add(task_record)
        await db.commit()
        await db.refresh(task_record)
        
        return created_response(
            data={
                "task_id": task.id,
                "task_type": "video_generation",
                "status": "pending",
            },
            message="Video generation task created successfully"
        )
    
    except Exception as e:
        logger.error(f"Async video generation error: {e}")
        raise AppException(
            status_code=500,
            error="TaskCreationError",
            message="Failed to create async video task"
        )


# ============================================
# IP-Adapter Smart Features
# ============================================


class SmartReferenceRequest(BaseModel):
    """Request model for smart reference selection."""
    ip_asset_id: int = Field(..., description="IP asset ID")
    prompt: str = Field(..., description="Generation prompt")
    max_images: int = Field(default=3, ge=1, le=5, description="Maximum number of reference images")


class ConsistencyCheckRequest(BaseModel):
    """Request model for consistency check."""
    generated_image_path: str = Field(..., description="Path to generated image")
    reference_images: List[str] = Field(..., description="List of reference image paths")
    threshold: float = Field(default=0.75, ge=0.0, le=1.0, description="Consistency threshold")


@router.post("/smart-references")
async def get_smart_references(
    request: SmartReferenceRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Intelligently select reference images based on prompt analysis.
    
    Analyzes the prompt for angle, expression, and pose attributes,
    then selects the best matching reference images from the IP asset.
    """
    try:
        logger.info(f"Smart reference selection for IP asset {request.ip_asset_id}")
        
        # Fetch IP asset
        result = await db.execute(select(IPAsset).where(IPAsset.id == request.ip_asset_id))
        ip_asset = result.scalar_one_or_none()
        
        if not ip_asset:
            raise NotFoundException(f"IP asset {request.ip_asset_id} not found")
        
        # Extract reference images
        reference_images = ip_asset.reference_images or []
        if not reference_images:
            raise BadRequestException("IP asset has no reference images")
        
        # Convert string paths to dict format if needed
        if isinstance(reference_images[0], str):
            reference_images = [{"path": path} for path in reference_images]
        
        # Select best references
        selected = ip_adapter_service.select_best_reference_images(
            reference_images=reference_images,
            prompt=request.prompt,
            max_images=request.max_images,
        )
        
        # Calculate adaptive scale
        use_lora = ip_asset.lora_model_id is not None
        adaptive_scale = ip_adapter_service.calculate_adaptive_scale(
            prompt=request.prompt,
            use_lora=use_lora,
        )
        
        # Analyze prompt
        prompt_analysis = ip_adapter_service.analyze_prompt(request.prompt)
        
        return success_response(
            data={
                "selected_references": selected,
                "adaptive_scale": adaptive_scale,
                "prompt_analysis": prompt_analysis,
                "total_available": len(reference_images),
            },
            message=f"Selected {len(selected)} reference images"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Smart reference selection error: {e}")
        raise AppException(
            status_code=500,
            error="ServerError",
            message="Failed to select reference images"
        )


@router.post("/check-consistency")
async def check_generation_consistency(
    request: ConsistencyCheckRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Check consistency between generated image and reference images.
    
    Uses CLIP similarity to measure character consistency.
    Returns score, pass/fail status, and recommendations.
    """
    try:
        logger.info(f"Consistency check for generated image")
        
        result = await ip_adapter_service.check_generated_consistency(
            generated_image_path=request.generated_image_path,
            reference_images=request.reference_images,
            threshold=request.threshold,
        )
        
        return success_response(
            data=result,
            message="Consistency check completed"
        )
        
    except Exception as e:
        logger.error(f"Consistency check error: {e}")
        raise AppException(
            status_code=500,
            error="ServerError",
            message="Failed to check consistency"
        )


@router.post("/adaptive-scale")
async def calculate_adaptive_scale(
    prompt: str,
    ip_asset_id: Optional[int] = None,
    use_lora: bool = False,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Calculate optimal IP-Adapter scale based on prompt analysis.
    
    Automatically adjusts scale based on:
    - Prompt context (character vs scene vs action)
    - LoRA usage (reduce to avoid overfitting)
    - Environment (indoor vs outdoor)
    """
    try:
        logger.info(f"Adaptive scale calculation for prompt")
        
        # If IP asset ID provided, check if LoRA is associated
        if ip_asset_id and not use_lora:
            result = await db.execute(select(IPAsset).where(IPAsset.id == ip_asset_id))
            ip_asset = result.scalar_one_or_none()
            if ip_asset:
                use_lora = ip_asset.lora_model_id is not None
            else:
                logger.warning(f"IP asset {ip_asset_id} not found, cannot determine LoRA usage")
        
        # Calculate adaptive scale
        scale = ip_adapter_service.calculate_adaptive_scale(
            prompt=prompt,
            use_lora=use_lora,
        )
        
        # Analyze prompt to explain the scale
        prompt_analysis = ip_adapter_service.analyze_prompt(prompt)
        
        return success_response(
            data={
                "scale": scale,
                "prompt_analysis": prompt_analysis,
                "use_lora": use_lora,
            },
            message=f"Adaptive scale: {scale}"
        )
        
    except Exception as e:
        logger.error(f"Adaptive scale calculation error: {e}")
        raise AppException(
            status_code=500,
            error="ServerError",
            message="Failed to calculate adaptive scale"
        )
