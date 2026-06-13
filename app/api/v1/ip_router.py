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
    ThreeViewGenerationRequest,
    ViewConfig,  # ✅ 新增：单个视图配置
)
from app.api.deps import get_current_user
from app.core.ip_manager import ip_manager
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    InternalServerError
)
from app.utils.logger import logger
from app.utils.response import success_response, list_response, created_response, updated_response, deleted_response, message_response
from celery_worker import generate_image_task

router = APIRouter(prefix="/api/v1/ip", tags=["IP Assets"])


@router.post("/{ip_id}/generate-three-views")
async def generate_three_views(
    ip_id: int,
    request: ThreeViewGenerationRequest = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate three views (front, side, back) for an IP asset.
    
    Supports parameter separation: shared parameters + independent view configurations.
    Reference images can be uploaded per view, or smart-selected from IP assets.
    """
    try:
        # 1. Get IP asset
        result = await db.execute(
            select(IPAsset).where(IPAsset.id == ip_id)
        )
        ip_asset = result.scalar_one_or_none()
        
        if not ip_asset:
            raise NotFoundException(resource="IP asset", identifier=str(ip_id))
        
        # 2. Get LoRA model path if available
        lora_path = None
        if ip_asset.lora_model_id:
            from app.models.lora_model import LoRAModel
            lora_result = await db.execute(
                select(LoRAModel).where(LoRAModel.id == ip_asset.lora_model_id)
            )
            lora_model = lora_result.scalar_one_or_none()
            if lora_model and lora_model.status == 'completed':
                lora_path = lora_model.file_path
        
        # 3. Parse generation parameters
        params = request.model_dump() if request else {}
        lora_weight = params.get("lora_weight", 0.7)
        # ✅ 优化：提高IP-Adapter Scale，增强参考图影响力
        ip_adapter_scale = params.get("ip_adapter_scale", 0.93)
        steps = params.get("steps", 30)
        # ✅ 优化：降低CFG Scale，减少prompt过度引导
        cfg_scale = params.get("cfg_scale", 5.5)
        width = params.get("width", 512)
        height = params.get("height", 512)
        seed = params.get("seed")
        # Default negative prompt includes facial protection keywords
        default_negative_tags = [
            "ugly", "deformed", "text",
            "asymmetric eyes", "deformed pupils", "deformed mouth",
            "extra fingers", "mutated hands", "bad anatomy",
            "blurry face", "distorted facial features",
        ]
        negative_prompt = params.get("negative_prompt") or ", ".join(
            ip_asset.negative_tags or default_negative_tags
        )
        
        # 4. Validate and build view configurations
        views_config = params.get("views")
        valid_view_types = {"front", "side", "back"}
        
        if views_config:
            # ✅ 优化：支持1-3个视图灵活生成
            if len(views_config) == 0 or len(views_config) > 3:
                raise BadRequestException(message="视图数量必须在1-3个之间")
            
            # Validate view_type
            provided_types = {view["view_type"] for view in views_config}
            invalid_types = provided_types - valid_view_types
            if invalid_types:
                raise BadRequestException(message=f"无效的视图类型: {invalid_types}")
            
            # Use frontend-provided prompts and reference images
            views = {
                view["view_type"]: {
                    "prompt": view["prompt"],
                    "negative_prompt": negative_prompt,
                    "reference_images": view.get("reference_images", [])
                }
                for view in views_config
            }
        else:
            # Use default prompt templates (精简版：IP-Adapter模式下只需视角+构图)
            # 角色外观、颜色、风格由参考图通过IP-Adapter提供
            views = {
                "front": {
                    "prompt": f"{ip_asset.trigger_word}, front view, full body, white background",
                    "negative_prompt": negative_prompt,
                    "reference_images": []  # Will use smart selection
                },
                "side": {
                    "prompt": f"{ip_asset.trigger_word}, side view, full body, white background",
                    "negative_prompt": negative_prompt,
                    "reference_images": []
                },
                "back": {
                    "prompt": f"{ip_asset.trigger_word}, back view, full body, white background",
                    "negative_prompt": negative_prompt,
                    "reference_images": []
                }
            }
        
        # 5. Reference image processing function
        def select_reference_images(view_config, ip_asset, view_type, max_count=1):
            """
            Select reference images with priority:
            1. User-uploaded images (if provided)
            2. Smart selection from IP asset reference images
            """
            # Priority 1: User-uploaded reference images
            if view_config.get('reference_images'):
                user_refs = view_config['reference_images']
                if len(user_refs) > 0:
                    logger.info(f"Using user-uploaded reference images for view_type={view_type}: {user_refs}")
                    return user_refs[:1]  # Max 1 image per view
            
            # Priority 2: Smart selection from IP asset
            reference_images = ip_asset.reference_images
            if not reference_images:
                logger.warning(f"No reference images available for view_type={view_type}")
                return []
            
            # Handle both dict and string formats
            if len(reference_images) > 0 and isinstance(reference_images[0], str):
                # Already string paths, just return first max_count
                logger.info(f"Reference images are already string paths for view_type={view_type}")
                return reference_images[:max_count]
            
            # Smart selection based on view_type angle matching (dict format)
            angle_priority = {
                "front": ["front", "half_body", "full_body"],
                "side": ["side", "profile"],
                "back": ["back"]
            }
            
            priority_angles = angle_priority.get(view_type, [])
            selected = []
            
            for angle in priority_angles:
                matching = [img["path"] for img in reference_images if img.get("angle") == angle]
                selected.extend(matching)
                if len(selected) >= max_count:
                    break
            
            if not selected:
                logger.warning(f"No matching reference images for view_type={view_type}, using fallback")
                selected = [img["path"] for img in reference_images[:max_count]]
            
            logger.info(f"Smart selected {len(selected)} reference images for view_type={view_type}")
            return selected[:max_count]
        
        # 6. Create async tasks for each view
        from app.models.task import TaskRecord
        from datetime import datetime
        
        task_ids = {}
        for view_name, view_data in views.items():
            # Process reference images (user-uploaded priority, otherwise smart selection)
            ref_images = select_reference_images(
                view_data,  # Contains reference_images field
                ip_asset,
                view_name,
                max_count=1  # Max 1 image per view
            )
            
            task = generate_image_task.apply_async(
                args=[
                    view_data["prompt"],
                    ip_asset.id,
                ],
                kwargs={
                    "channel_id": None,  # Use local model
                    "lora_path": lora_path,
                    "lora_weight": lora_weight,
                    "use_ip_adapter": True,
                    "reference_images": ref_images,  # Processed reference images
                    "negative_prompt": view_data["negative_prompt"],
                    "ip_adapter_scale": ip_adapter_scale,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg_scale": cfg_scale,
                    "view_type": view_name,  # Pass to Celery task
                    "seed": seed,  # Optional seed
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
                    "negative_prompt": view_data["negative_prompt"],
                    "view_type": view_name,
                    "use_ip_adapter": True,
                    "reference_images": ref_images,  # Use processed reference images
                    "lora_weight": lora_weight,
                    "ip_adapter_scale": ip_adapter_scale,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg_scale": cfg_scale,
                },
                created_by=current_user.get("id", 1),
                created_at=datetime.now(),  # Use local time to match started_at
            )
            
            db.add(task_record)
            
            task_ids[view_name] = task.id
        
        # Commit all task records
        await db.commit()
        
        logger.info(
            f"Views generation tasks created for IP {ip_id}: {task_ids} ({len(task_ids)} views)"
        )
        
        return success_response(
            data={
                "task_ids": task_ids,
                "ip_id": ip_id,
                "ip_name": ip_asset.name,
                "views_count": len(task_ids),
                "message": f"{len(task_ids)}个视图生成任务已创建"
            },
            message=f"{len(task_ids)}个视图生成任务已创建"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Failed to create views tasks for IP {ip_id}: {e}", exc_info=True)
        raise InternalServerError(message="Failed to create views generation tasks")


@router.post("/{ip_id}/generate-view/{view_type}")
async def generate_single_view(
    ip_id: int,
    view_type: str,
    request: dict = None,  # ✅ 修改：使用dict而非ViewConfig，避免view_type重复
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate a single view (front/side/back) for an IP asset.
    
    This is a convenience endpoint for generating individual views.
    """
    try:
        # 1. Validate view_type
        valid_view_types = {"front", "side", "back"}
        if view_type not in valid_view_types:
            raise BadRequestException(message=f"Invalid view type: {view_type}. Must be one of: {valid_view_types}")
        
        # 2. Get IP asset
        result = await db.execute(
            select(IPAsset).where(IPAsset.id == ip_id)
        )
        ip_asset = result.scalar_one_or_none()
        
        if not ip_asset:
            raise NotFoundException(resource="IP asset", identifier=str(ip_id))
        
        # 3. Get LoRA model path if available
        lora_path = None
        if ip_asset.lora_model_id:
            from app.models.lora_model import LoRAModel
            lora_result = await db.execute(
                select(LoRAModel).where(LoRAModel.id == ip_asset.lora_model_id)
            )
            lora_model = lora_result.scalar_one_or_none()
            if lora_model and lora_model.status == 'completed':
                lora_path = lora_model.file_path
        
        # 4. Parse generation parameters
        params = request if request else {}
        lora_weight = params.get("lora_weight", 0.7)
        ip_adapter_scale = params.get("ip_adapter_scale", 0.93)
        steps = params.get("steps", 30)
        cfg_scale = params.get("cfg_scale", 5.5)
        width = params.get("width", 512)
        height = params.get("height", 512)
        seed = params.get("seed")
        # Default negative prompt includes facial protection keywords
        default_negative_tags = [
            "ugly", "deformed", "text",
            "asymmetric eyes", "deformed pupils", "deformed mouth",
            "extra fingers", "mutated hands", "bad anatomy",
            "blurry face", "distorted facial features",
        ]
        negative_prompt = params.get("negative_prompt") or ", ".join(
            ip_asset.negative_tags or default_negative_tags
        )
        
        # 5. Build view configuration
        prompt = params.get("prompt") or f"{ip_asset.trigger_word}, {view_type} view, full body, white background"
        reference_images = params.get("reference_images", [])
        
        # 6. Reference image processing
        def select_reference_images(ip_asset, view_type, max_count=1):
            """Select reference images with priority"""
            # Priority 1: User-provided reference images
            if reference_images and len(reference_images) > 0:
                logger.info(f"Using user-provided reference images for view_type={view_type}")
                return reference_images[:max_count]
            
            # Priority 2: Smart selection from IP asset
            ip_reference_images = ip_asset.reference_images
            if not ip_reference_images:
                logger.warning(f"No reference images available for view_type={view_type}")
                return []
            
            # Handle both dict and string formats
            if len(ip_reference_images) > 0 and isinstance(ip_reference_images[0], str):
                logger.info(f"Reference images are already string paths for view_type={view_type}")
                return ip_reference_images[:max_count]
            
            # Smart selection based on view_type angle matching
            angle_priority = {
                "front": ["front", "half_body", "full_body"],
                "side": ["side", "profile"],
                "back": ["back"]
            }
            
            priority_angles = angle_priority.get(view_type, [])
            selected = []
            
            for angle in priority_angles:
                matching = [img["path"] for img in ip_reference_images if img.get("angle") == angle]
                selected.extend(matching)
                if len(selected) >= max_count:
                    break
            
            if not selected:
                logger.warning(f"No matching reference images for view_type={view_type}, using fallback")
                selected = [img["path"] for img in ip_reference_images[:max_count]]
            
            logger.info(f"Smart selected {len(selected)} reference images for view_type={view_type}")
            return selected[:max_count]
        
        ref_images = select_reference_images(ip_asset, view_type, max_count=1)
        
        # 7. Create async task
        from app.models.task import TaskRecord
        from datetime import datetime
        
        task = generate_image_task.apply_async(
            args=[
                prompt,
                ip_asset.id,
            ],
            kwargs={
                "channel_id": None,
                "lora_path": lora_path,
                "lora_weight": lora_weight,
                "use_ip_adapter": True,
                "reference_images": ref_images,
                "negative_prompt": negative_prompt,
                "ip_adapter_scale": ip_adapter_scale,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "view_type": view_type,
                "seed": seed,
            },
            queue="image_generation"
        )
        
        # Create task record
        task_record = TaskRecord(
            task_id=task.id,
            task_type="image_generation",
            ip_asset_id=ip_asset.id,
            status="pending",
            parameters={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "view_type": view_type,
                "use_ip_adapter": True,
                "reference_images": ref_images,
                "lora_weight": lora_weight,
                "ip_adapter_scale": ip_adapter_scale,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
            },
            created_by=current_user.get("id", 1),
            created_at=datetime.now(),
        )
        
        db.add(task_record)
        await db.commit()
        
        logger.info(f"Single view generation task created for IP {ip_id}, view_type={view_type}: {task.id}")
        
        return success_response(
            data={
                "task_id": task.id,
                "ip_id": ip_id,
                "ip_name": ip_asset.name,
                "view_type": view_type,
                "message": f"{view_type} view generation task created successfully"
            },
            message=f"{view_type}视图生成任务已创建"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Failed to create single view task for IP {ip_id}, view_type={view_type}: {e}", exc_info=True)
        raise InternalServerError(message="Failed to create view generation task")


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
        logger.error(f"Failed to create IP asset: {e}", exc_info=True)
        raise InternalServerError(
            message="Failed to create IP asset",
            details={"original_error": str(e)}
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
        
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Failed to list IP assets: {e}", exc_info=True)
        raise InternalServerError(message="Failed to list IP assets")


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
        logger.error(f"Failed to get IP asset: {e}", exc_info=True)
        raise InternalServerError(message="Failed to get IP asset")


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
        logger.error(f"Failed to update IP asset: {e}", exc_info=True)
        raise InternalServerError(message="Failed to update IP asset")


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
        logger.error(f"Failed to delete IP asset: {e}", exc_info=True)
        raise InternalServerError(message="Failed to delete IP asset")
