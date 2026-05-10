"""
IP Asset Router

API endpoints for IP character asset management including
CRUD operations and listing.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.config.database import get_db_session
from app.models.ip_asset import IPAsset
from app.schemas.ip_schema import (
    IPAssetCreate,
    IPAssetUpdate,
    IPAssetResponse,
    IPAssetListResponse,
)
from app.api.deps import get_current_user
from app.core.ip_manager import ip_manager
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    AppException
)
from app.utils.logger import logger
from app.utils.response import success_response, list_response, created_response, updated_response, deleted_response, message_response
from celery_worker import generate_image_task

router = APIRouter(prefix="/api/v1/ip", tags=["IP Assets"])


@router.post("/{ip_id}/generate-three-views")
async def generate_three_views(
    ip_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate three views (front, side, back) for an IP asset.
    
    Requires authentication and IP must have reference images.
    """
    try:
        # Get IP asset
        result = await db.execute(
            select(IPAsset).where(IPAsset.id == ip_id)
        )
        ip_asset = result.scalar_one_or_none()
        
        if not ip_asset:
            raise NotFoundException(
                message=f"IP asset {ip_id} not found",
                details={"ip_id": ip_id}
            )
        
        # Check if has reference images
        if not ip_asset.reference_images or len(ip_asset.reference_images) == 0:
            raise BadRequestException(
                message="IP asset has no reference images. Please upload reference images first.",
                details={"ip_id": ip_id}
            )
        
        # Extract reference image paths
        reference_images = []
        for img in ip_asset.reference_images:
            if isinstance(img, dict):
                reference_images.append(img.get('path', ''))
            else:
                reference_images.append(str(img))
        
        reference_images = [p for p in reference_images if p]  # Filter empty
        
        if not reference_images:
            raise BadRequestException(
                message="No valid reference image paths found",
                details={"ip_id": ip_id}
            )
        
        # Get LoRA model path if available
        lora_path = None
        if ip_asset.lora_model_id:
            from app.models.lora_model import LoRAModel
            lora_result = await db.execute(
                select(LoRAModel).where(LoRAModel.id == ip_asset.lora_model_id)
            )
            lora_model = lora_result.scalar_one_or_none()
            if lora_model and lora_model.status == 'completed':
                lora_path = lora_model.file_path
        
        # Define three views with specific prompts
        views = {
            "front": {
                "prompt": f"{ip_asset.name}, front view, facing camera, full body, clean white background, masterpiece, best quality, {ip_asset.style_template or '3d_cartoon'} style",
                "negative_prompt": "side view, back view, multiple views, ugly, deformed, blurry, low quality"
            },
            "side": {
                "prompt": f"{ip_asset.name}, side view, profile, 90 degrees, full body, clean white background, masterpiece, best quality, {ip_asset.style_template or '3d_cartoon'} style",
                "negative_prompt": "front view, back view, multiple views, ugly, deformed, blurry, low quality"
            },
            "back": {
                "prompt": f"{ip_asset.name}, back view, from behind, full body, clean white background, masterpiece, best quality, {ip_asset.style_template or '3d_cartoon'} style",
                "negative_prompt": "front view, side view, multiple views, ugly, deformed, blurry, low quality"
            }
        }
        
        # Create async tasks for each view
        from app.models.task import TaskRecord
        from datetime import datetime
        
        task_ids = {}
        for view_name, view_data in views.items():
            task = generate_image_task.apply_async(
                args=[
                    view_data["prompt"],
                    ip_asset.id,
                ],
                kwargs={
                    "channel_id": None,  # Use local model
                    "lora_path": lora_path,
                    "lora_weight": 0.7,
                    "use_ip_adapter": True,
                    "reference_images": reference_images,
                    "ip_adapter_scale": 0.8,
                    "width": 512,
                    "height": 512,
                    "steps": 30,
                    "cfg_scale": 7.0,
                    # view_type removed - not supported by generate_image()
                },
                queue="image_generation"
            )
            
            # Create task record in database with explicit local time
            task_record = TaskRecord(
                task_id=task.id,
                task_type="image_generation",
                ip_asset_id=ip_asset.id,
                status="pending",
                parameters={
                    "prompt": view_data["prompt"],
                    "view_type": view_name,
                    "use_ip_adapter": True,
                    "reference_images": reference_images,
                    "width": 512,
                    "height": 512,
                    "steps": 30,
                    "cfg_scale": 7.0,
                },
                created_by=current_user.get("id", 1),
                created_at=datetime.now(),  # Use local time to match started_at
            )
            
            db.add(task_record)
            
            task_ids[view_name] = task.id
        
        # Commit all task records
        await db.commit()
        
        logger.info(
            f"Three views generation tasks created for IP {ip_id}: {task_ids}"
        )
        
        return success_response(
            data={
                "task_ids": task_ids,
                "ip_id": ip_id,
                "ip_name": ip_asset.name,
                "message": "Three views generation tasks created successfully"
            },
            message="三视图生成任务已创建"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Failed to create three views tasks for IP {ip_id}: {e}")
        raise AppException(
            status_code=500,
            error="TaskCreationError",
            message="Failed to create three views generation tasks"
        )


@router.post("/create", status_code=201)
async def create_ip_asset(
    ip_data: IPAssetCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new IP character asset.
    
    Requires authentication.
    """
    try:
        # Check if trigger word already exists
        result = await db.execute(
            select(IPAsset).where(IPAsset.trigger_word == ip_data.trigger_word)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ConflictException(
                message=f"Trigger word '{ip_data.trigger_word}' already exists",
                details={"field": "trigger_word", "value": ip_data.trigger_word}
            )
        
        # Create IP asset using manager
        ip_asset = await ip_manager.create_ip_asset(ip_data)
        
        logger.info(f"IP asset '{ip_asset.name}' created by user {current_user['username']}")
        
        return created_response(
            data={
                "id": ip_asset.id,
                "name": ip_asset.name,
                "description": ip_asset.description,
                "category": ip_asset.category,
                "trigger_word": ip_asset.trigger_word,
                "style_template": ip_asset.style_template,
                "reference_images": ip_asset.reference_images or [],
                "positive_tags": ip_asset.positive_tags,
                "negative_tags": ip_asset.negative_tags,
                "lora_model_id": ip_asset.lora_model_id,
                "created_at": ip_asset.created_at,
                "updated_at": ip_asset.updated_at,
            },
            message="IP asset created successfully"
        )
        
    except (ConflictException,):
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to create IP asset"
        )


@router.get("/list")
async def list_ip_assets(
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List IP assets with pagination.
    
    Optional category filter.
    """
    try:
        # Build query
        query = select(IPAsset)
        count_query = select(func.count(IPAsset.id))
        
        if category:
            query = query.where(IPAsset.category == category)
            count_query = count_query.where(IPAsset.category == category)
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get items with pagination - sort by updated_at descending (most recent first)
        query = query.offset(skip).limit(limit).order_by(IPAsset.updated_at.desc())
        result = await db.execute(query)
        items = result.scalars().all()
        
        # Convert items to dict
        item_list = []
        for item in items:
            item_list.append({
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "category": item.category,
                "trigger_word": item.trigger_word,
                "style_template": item.style_template,
                "reference_images": item.reference_images or [],
                "positive_tags": item.positive_tags,
                "negative_tags": item.negative_tags,
                "lora_model_id": item.lora_model_id,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            })
        
        return list_response(
            items=item_list,
            page=(skip // limit) + 1 if limit > 0 else 1,
            page_size=limit,
            total=total or 0
        )
        
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to list IP assets"
        )


@router.get("/{ip_id}")
async def get_ip_asset(
    ip_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get a specific IP asset by ID.
    """
    try:
        result = await db.execute(
            select(IPAsset).where(IPAsset.id == ip_id)
        )
        ip_asset = result.scalar_one_or_none()
        
        if not ip_asset:
            raise NotFoundException(resource="IPAsset", identifier=str(ip_id))
        
        return success_response(
            data={
                "id": ip_asset.id,
                "name": ip_asset.name,
                "description": ip_asset.description,
                "category": ip_asset.category,
                "trigger_word": ip_asset.trigger_word,
                "style_template": ip_asset.style_template,
                "reference_images": ip_asset.reference_images or [],
                "positive_tags": ip_asset.positive_tags,
                "negative_tags": ip_asset.negative_tags,
                "lora_model_id": ip_asset.lora_model_id,
                "created_at": ip_asset.created_at,
                "updated_at": ip_asset.updated_at,
            }
        )
        
    except NotFoundException:
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to get IP asset"
        )


@router.put("/{ip_id}")
async def update_ip_asset(
    ip_id: int,
    update_data: IPAssetUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update an existing IP asset.
    """
    try:
        result = await db.execute(
            select(IPAsset).where(IPAsset.id == ip_id)
        )
        ip_asset = result.scalar_one_or_none()
        
        if not ip_asset:
            raise NotFoundException(resource="IPAsset", identifier=str(ip_id))
        
        # Update fields
        update_fields = update_data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(ip_asset, field, value)
        
        await db.commit()
        await db.refresh(ip_asset)
        
        logger.info(f"IP asset '{ip_asset.name}' updated by user {current_user['username']}")
        
        return updated_response(
            data={
                "id": ip_asset.id,
                "name": ip_asset.name,
                "description": ip_asset.description,
                "category": ip_asset.category,
                "trigger_word": ip_asset.trigger_word,
                "style_template": ip_asset.style_template,
                "reference_images": ip_asset.reference_images or [],
                "positive_tags": ip_asset.positive_tags,
                "negative_tags": ip_asset.negative_tags,
                "lora_model_id": ip_asset.lora_model_id,
                "created_at": ip_asset.created_at,
                "updated_at": ip_asset.updated_at,
            },
            message="IP asset updated successfully"
        )
        
    except NotFoundException:
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to update IP asset"
        )


@router.delete("/{ip_id}", status_code=204)
async def delete_ip_asset(
    ip_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete an IP asset.
    """
    try:
        result = await db.execute(
            select(IPAsset).where(IPAsset.id == ip_id)
        )
        ip_asset = result.scalar_one_or_none()
        
        if not ip_asset:
            raise NotFoundException(resource="IPAsset", identifier=str(ip_id))
        
        await db.delete(ip_asset)
        await db.commit()
        
        logger.info(f"IP asset '{ip_asset.name}' deleted by user {current_user['username']}")
        
        return None
        
    except NotFoundException:
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to delete IP asset"
        )
