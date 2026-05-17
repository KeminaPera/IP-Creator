"""
IP Feature Library Router

API endpoints for managing IP feature library including:
- Multi-view management (front/side/back views)
- Feature library (outfits, expressions, poses, etc.)
- Feature images management
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List
from pathlib import Path
import os

from app.config.database import get_db_session
from app.models.ip_multi_view import IPMultiView
from app.models.ip_feature_library import IPFeatureLibrary
from app.models.ip_feature_image import IPFeatureImage
from app.schemas.ip_feature_schema import (
    MultiViewCreate, MultiViewResponse, MultiViewListResponse,
    FeatureCreate, FeatureUpdate, FeatureResponse, FeatureListResponse,
    FeatureImageCreate, FeatureImageResponse,
    FeatureTypeListResponse,
    BatchFeatureCreate
)
from app.utils.response import success_response, created_response, updated_response, deleted_response
from app.api.deps import get_current_user
from app.config.feature_types import get_feature_types, get_feature_type, is_feature_type_valid, get_trigger_phrase
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/ip", tags=["IP Features"])


# ============================================
# Feature Type Configuration Endpoint (必须在参数路由之前)
# ============================================

@router.get("/feature-types")
async def get_feature_types_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """Get all supported feature types configuration."""
    types = get_feature_types()
    return success_response(
        data=types,
        message="Feature types retrieved successfully"
    )


# ============================================
# Multi-View Endpoints
# ============================================

@router.post("/{ip_id}/multi-views", status_code=201)
async def create_multi_view(
    ip_id: int,
    view_data: MultiViewCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new multi-view for an IP asset."""
    # Verify IP exists
    from app.models.ip_asset import IPAsset
    ip_result = await db.execute(select(IPAsset).where(IPAsset.id == ip_id))
    ip_asset = ip_result.scalar_one_or_none()
    if not ip_asset:
        raise HTTPException(status_code=404, detail="IP asset not found")
    
    # Create multi-view
    multi_view = IPMultiView(
        ip_asset_id=ip_id,
        **view_data.model_dump()
    )
    db.add(multi_view)
    await db.commit()
    await db.refresh(multi_view)
    
    return created_response(
        data=MultiViewResponse.model_validate(multi_view),
        message="Multi-view created successfully"
    )


@router.get("/{ip_id}/multi-views")
async def get_multi_views(
    ip_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all multi-views for an IP asset."""
    result = await db.execute(
        select(IPMultiView)
        .where(IPMultiView.ip_asset_id == ip_id)
        .order_by(IPMultiView.view_type)
    )
    views = result.scalars().all()
    
    return success_response(
        data=[MultiViewResponse.model_validate(v) for v in views],
        message="Multi-views retrieved successfully"
    )


@router.delete("/{ip_id}/multi-views/{view_id}")
async def delete_multi_view(
    ip_id: int,
    view_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a multi-view."""
    result = await db.execute(
        select(IPMultiView).where(
            IPMultiView.id == view_id,
            IPMultiView.ip_asset_id == ip_id
        )
    )
    view = result.scalar_one_or_none()
    if not view:
        raise HTTPException(status_code=404, detail="Multi-view not found")
    
    # 删除资源文件（如果是新资源路径格式）
    if view.image_path and view.image_path.startswith('data/resources/'):
        try:
            resource_path = Path(view.image_path)
            if resource_path.exists():
                resource_path.unlink()
                logger.info(f"Deleted multi-view resource: {view.image_path}")
        except Exception as e:
            # 记录错误但不阻止删除操作
            logger.warning(f"Failed to delete resource file {view.image_path}: {e}")
    
    await db.delete(view)
    await db.commit()
    
    return success_response(data={"id": view_id}, message="Multi-view deleted successfully")


# ============================================
# Feature Library Endpoints
# ============================================

@router.post("/{ip_id}/features", status_code=201)
async def create_feature(
    ip_id: int,
    feature_data: FeatureCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new feature for an IP asset."""
    # Verify IP exists
    from app.models.ip_asset import IPAsset
    ip_result = await db.execute(select(IPAsset).where(IPAsset.id == ip_id))
    ip_asset = ip_result.scalar_one_or_none()
    if not ip_asset:
        raise HTTPException(status_code=404, detail="IP asset not found")
    
    # Validate feature type
    if not is_feature_type_valid(feature_data.feature_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feature type: {feature_data.feature_type}. Valid types: outfit, expression, pose"
        )
    
    # Check uniqueness
    existing = await db.execute(
        select(IPFeatureLibrary).where(
            IPFeatureLibrary.ip_asset_id == ip_id,
            IPFeatureLibrary.feature_type == feature_data.feature_type,
            IPFeatureLibrary.feature_name == feature_data.feature_name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Feature {feature_data.feature_name} already exists for this IP"
        )
    
    # Auto-generate trigger phrase if not provided
    if not feature_data.trigger_phrase:
        feature_data.trigger_phrase = get_trigger_phrase(
            feature_data.feature_type,
            feature_data.feature_name
        )
    
    # Create feature
    feature = IPFeatureLibrary(
        ip_asset_id=ip_id,
        **feature_data.model_dump()
    )
    db.add(feature)
    await db.commit()
    await db.refresh(feature)
    
    # Reload with images relationship
    result = await db.execute(
        select(IPFeatureLibrary)
        .where(IPFeatureLibrary.id == feature.id)
    )
    feature = result.scalar_one()
    
    return created_response(
        data=FeatureResponse.model_validate(feature),
        message="Feature created successfully"
    )


@router.get("/{ip_id}/features")
async def get_features(
    ip_id: int,
    feature_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all features for an IP asset, optionally filtered by type."""
    query = select(IPFeatureLibrary).where(IPFeatureLibrary.ip_asset_id == ip_id)
    
    if feature_type:
        query = query.where(IPFeatureLibrary.feature_type == feature_type)
    
    query = query.order_by(IPFeatureLibrary.feature_type, IPFeatureLibrary.feature_name)
    
    result = await db.execute(query)
    features = result.scalars().all()
    
    return success_response(
        data=[FeatureResponse.model_validate(f) for f in features],
        message="Features retrieved successfully"
    )


@router.get("/{ip_id}/features/{feature_id}")
async def get_feature(
    ip_id: int,
    feature_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get a specific feature."""
    result = await db.execute(
        select(IPFeatureLibrary).where(
            IPFeatureLibrary.id == feature_id,
            IPFeatureLibrary.ip_asset_id == ip_id
        )
    )
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    return success_response(
        data=FeatureResponse.model_validate(feature),
        message="Feature retrieved successfully"
    )


@router.patch("/{ip_id}/features/{feature_id}")
async def update_feature(
    ip_id: int,
    feature_id: int,
    feature_data: FeatureUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update a feature."""
    result = await db.execute(
        select(IPFeatureLibrary).where(
            IPFeatureLibrary.id == feature_id,
            IPFeatureLibrary.ip_asset_id == ip_id
        )
    )
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    # Update fields
    update_data = feature_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(feature, key, value)
    
    await db.commit()
    await db.refresh(feature)
    
    # Reload with images
    result = await db.execute(
        select(IPFeatureLibrary).where(IPFeatureLibrary.id == feature_id)
    )
    feature = result.scalar_one()
    
    return updated_response(
        data=FeatureResponse.model_validate(feature),
        message="Feature updated successfully"
    )


@router.delete("/{ip_id}/features/{feature_id}")
async def delete_feature(
    ip_id: int,
    feature_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a feature and all its images."""
    result = await db.execute(
        select(IPFeatureLibrary).where(
            IPFeatureLibrary.id == feature_id,
            IPFeatureLibrary.ip_asset_id == ip_id
        )
    )
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    # Delete associated images files
    for image in feature.images:
        if image.image_path and image.image_path.startswith('data/resources/'):
            try:
                resource_path = Path(image.image_path)
                if resource_path.exists():
                    resource_path.unlink()
                    logger.info(f"Deleted feature image resource: {image.image_path}")
            except Exception as e:
                logger.warning(f"Failed to delete resource file {image.image_path}: {e}")
    
    await db.delete(feature)
    await db.commit()
    
    return success_response(data={"id": feature_id}, message="Feature deleted successfully")


# ============================================
# Feature Image Endpoints
# ============================================

@router.post("/features/{feature_id}/images", status_code=201)
async def create_feature_image(
    feature_id: int,
    image_data: FeatureImageCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Add an image to a feature."""
    # Verify feature exists
    result = await db.execute(
        select(IPFeatureLibrary).where(IPFeatureLibrary.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    # Create image record
    image = IPFeatureImage(
        feature_id=feature_id,
        **image_data.model_dump()
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    
    return created_response(
        data=FeatureImageResponse.model_validate(image),
        message="Feature image added successfully"
    )


@router.get("/features/{feature_id}/images")
async def get_feature_images(
    feature_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all images for a feature."""
    result = await db.execute(
        select(IPFeatureImage)
        .where(IPFeatureImage.feature_id == feature_id)
        .order_by(IPFeatureImage.angle)
    )
    images = result.scalars().all()
    
    return success_response(
        data=[FeatureImageResponse.model_validate(img) for img in images]
    )


@router.delete("/features/{feature_id}/images/{image_id}")
async def delete_feature_image(
    feature_id: int,
    image_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a feature image."""
    result = await db.execute(
        select(IPFeatureImage).where(
            IPFeatureImage.id == image_id,
            IPFeatureImage.feature_id == feature_id
        )
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete file
    if image.image_path and image.image_path.startswith('data/resources/'):
        try:
            resource_path = Path(image.image_path)
            if resource_path.exists():
                resource_path.unlink()
                logger.info(f"Deleted feature image resource: {image.image_path}")
        except Exception as e:
            logger.warning(f"Failed to delete resource file {image.image_path}: {e}")
    
    await db.delete(image)
    await db.commit()
    
    return success_response(data={"id": image_id}, message="Image deleted successfully")
