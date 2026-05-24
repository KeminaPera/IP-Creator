"""
System Settings Router

API endpoints for managing system-wide configuration settings.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.config.database import get_db_session
from app.api.deps import get_current_user
from app.services.settings_service import settings_service
from app.models.system_setting import SystemSetting
from app.utils.response import success_response
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/settings", tags=["System Settings"])


@router.get("/")
async def get_all_settings(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all system settings grouped by category
    
    Returns:
        All settings organized by category
    """
    try:
        settings = await settings_service.get_all_settings(db)
        return success_response(data=settings)
    except Exception as e:
        logger.error(f"Failed to get all settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{category}")
async def get_settings_by_category(
    category: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get settings for a specific category
    
    Args:
        category: Setting category (llm_default, resource_limit, storage_path, system_feature)
        
    Returns:
        Settings for the specified category
    """
    try:
        settings = await settings_service.get_settings_by_category(db, category)
        return success_response(data=settings)
    except Exception as e:
        logger.error(f"Failed to get settings for category {category}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{category}/{key}")
async def get_setting_detail(
    category: str,
    key: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific setting
    
    Args:
        category: Setting category
        key: Setting key
        
    Returns:
        Detailed setting information including metadata
    """
    try:
        setting = await settings_service.get_setting_detail(db, category, key)
        
        if not setting:
            raise HTTPException(
                status_code=404,
                detail=f"Setting not found: {category}.{key}"
            )
        
        return success_response(data=setting)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get setting detail {category}.{key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{category}/{key}")
async def update_setting(
    category: str,
    key: str,
    request_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a specific setting
    
    Args:
        category: Setting category
        key: Setting key
        request_data: {"value": new_value}
        
    Returns:
        Success message
    """
    try:
        value = request_data.get('value')
        
        if value is None:
            raise HTTPException(
                status_code=400,
                detail="Value is required in request body"
            )
        
        await settings_service.update_setting(
            db,
            category,
            key,
            value,
            user_id=current_user.get('id')
        )
        
        return success_response(
            message=f"Setting {category}.{key} updated successfully",
            data={"category": category, "key": key, "value": value}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update setting {category}.{key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{category}/reset")
async def reset_category_settings(
    category: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    Reset all settings in a category to their default values
    
    Args:
        category: Setting category to reset
        
    Returns:
        Number of settings reset
    """
    try:
        count = await settings_service.reset_to_default(
            db,
            category,
            user_id=current_user.get('id')
        )
        
        return success_response(
            message=f"Reset {count} settings to default for category: {category}",
            data={"category": category, "reset_count": count}
        )
    except Exception as e:
        logger.error(f"Failed to reset settings for category {category}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user)
):
    """
    List all available setting categories
    
    Returns:
        List of category names
    """
    try:
        result = await db.execute(
            select(distinct(SystemSetting.category)).where(
                SystemSetting.is_active == True
            )
        )
        categories = [row[0] for row in result.fetchall()]
        
        return success_response(data=categories)
    except Exception as e:
        logger.error(f"Failed to list categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
