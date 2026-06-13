"""
LLM Configuration API Router

Endpoints for managing LLM model configurations,
health checks, and hot-switching.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List
from app.config.database import get_db_session
from app.models.llm_model import LLMConfig
from app.models.llm_provider import LLMProvider, LLMModel
from app.schemas.llm_schema import (
    LLMConfigCreate,
    LLMConfigUpdate,
    LLMConfigResponse,
    LLMHealthStatus,
    LLMSwitchRequest,
)
from app.core.llm_manager import llm_manager, llm_registry
from app.core.llm_provider_registry import get_all_providers, get_provider_models, get_provider_by_id
from app.core.generation_dispatcher import generation_dispatcher
from app.security.crypto import encryption_service
from app.api.deps import require_admin
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    AppException
)
from app.utils.logger import logger
from app.utils.response import success_response, list_response, created_response, updated_response, deleted_response, message_response

router = APIRouter(prefix="/api/v1/llm", tags=["LLM Management"])


@router.post("/register", status_code=201)
async def register_llm(
    llm_data: LLMConfigCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """Register a new LLM model configuration."""
    # Encrypt API key if provided
    api_key_encrypted = None
    if llm_data.api_key:
        api_key_encrypted = encryption_service.encrypt(llm_data.api_key)
    
    # Create database record
    db_llm = LLMConfig(
        name=llm_data.name,
        model_type=llm_data.model_type,
        provider=llm_data.provider,
        model_name=llm_data.model_name,
        api_endpoint=llm_data.api_endpoint,
        api_key_encrypted=api_key_encrypted,
        local_path=llm_data.local_path,
        temperature=llm_data.temperature,
        max_tokens=llm_data.max_tokens,
        timeout=llm_data.timeout,
        context_window=llm_data.context_window,
        additional_params=llm_data.additional_params,
        description=llm_data.description,
    )
    
    db.add(db_llm)
    try:
        await db.commit()
        await db.refresh(db_llm)
    except IntegrityError:
        await db.rollback()
        raise ConflictException(
            message=f"Channel already exists for provider '{llm_data.provider}' with model '{llm_data.model_name}'. "
                   f"Each provider+model combination can only have one channel.",
            details={"provider": llm_data.provider, "model_name": llm_data.model_name}
        )
    
    # Register in runtime
    await llm_manager.register_model(db_llm)
    
    return created_response(
        data={
            "id": db_llm.id,
            "name": db_llm.name,
            "model_type": db_llm.model_type,
            "provider": db_llm.provider,
            "model_name": db_llm.model_name,
        },
        message="LLM channel registered successfully"
    )


@router.get("/list")
async def list_llms(
    db: AsyncSession = Depends(get_db_session),
):
    """List all registered LLM models."""
    result = await db.execute(select(LLMConfig))
    llms = result.scalars().all()
    
    # Mask API keys in response and add provider icon
    response_list = []
    for llm in llms:
        # Get provider icon (async)
        provider = await get_provider_by_id(llm.provider)
        provider_icon = provider.icon if provider else "fas fa-brain"
        provider_icon_url = provider.icon_url if provider else None
        provider_name = provider.name if provider else llm.provider
        
        # Get model capabilities from llm_models
        model_capabilities = None
        provider_result = await db.execute(
            select(LLMProvider).where(LLMProvider.code == llm.provider)
        )
        db_provider = provider_result.scalar_one_or_none()
        if db_provider:
            model_result = await db.execute(
                select(LLMModel).where(
                    LLMModel.provider_id == db_provider.id,
                    LLMModel.code == llm.model_name,
                )
            )
            db_model = model_result.scalar_one_or_none()
            if db_model and db_model.capabilities:
                model_capabilities = db_model.capabilities
        
        llm_dict = {
            "id": llm.id,
            "name": llm.name,
            "model_type": llm.model_type,
            "provider": llm.provider,
            "provider_name": provider_name,
            "provider_icon": provider_icon,
            "provider_icon_url": provider_icon_url,
            "model_name": llm.model_name,
            "api_endpoint": llm.api_endpoint,
            "api_key_masked": encryption_service.mask_sensitive(
                encryption_service.decrypt(llm.api_key_encrypted)
            ) if llm.api_key_encrypted else None,
            "local_path": llm.local_path,
            "temperature": llm.temperature,
            "max_tokens": llm.max_tokens,
            "timeout": llm.timeout,
            "context_window": llm.context_window,
            "additional_params": llm.additional_params,
            "is_active": llm.is_active,
            "is_default": llm.is_default,
            "health_status": llm.health_status,
            "last_health_check": llm.last_health_check,
            "response_time_ms": llm.response_time_ms,
            "success_rate": llm.success_rate,
            "capabilities": model_capabilities,
            "created_at": llm.created_at,
            "updated_at": llm.updated_at,
        }
        response_list.append(llm_dict)
    
    return success_response(data=response_list)


@router.put("/switch")
async def switch_llm(
    switch_data: LLMSwitchRequest,
    admin: dict = Depends(require_admin),
):
    """Hot-switch to a different LLM model."""
    success = await llm_manager.switch_model(switch_data.model_id)
    
    if not success:
        raise BadRequestException(
            message=f"Failed to switch to model {switch_data.model_id}",
            details={"model_id": switch_data.model_id}
        )
    
    return message_response(
        message=f"Successfully switched to model {switch_data.model_id}"
    )


@router.get("/health/all")
async def check_all_llms_health():
    """Check health status of all registered LLM models."""
    results = await llm_manager.health_check_all_models()
    return success_response(data=results)


@router.get("/health/{model_id}")
async def check_llm_health(
    model_id: int,
):
    """Check health status of a specific LLM model."""
    health = await llm_manager.health_check_model(model_id)
    
    return success_response(
        data={
            "model_id": model_id,
            "model_name": health.get("model", "unknown"),
            "health_status": health.get("status", "unknown"),
            "response_time_ms": health.get("response_time_ms"),
            "error_message": health.get("error"),
        }
    )


@router.get("/channels/by-capability")
async def get_channels_by_capability(
    capability: str,
):
    """
    Get all active channels that support a given capability.
    
    Used by the generate page to populate model selectors filtered by tag.
    
    Args:
        capability: Capability tag to filter by (e.g., 'text_generation', 'text_to_image', 'text_to_video')
    
    Returns:
        List of channels with matching capabilities
    """
    channels = await generation_dispatcher.get_channels_by_capability(capability)
    return success_response(data=channels)


# Provider and model listing endpoints have been moved to provider_router.py
# to support database-driven provider management.


@router.put("/{model_id}")
async def update_llm(
    model_id: int,
    update_data: LLMConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """Update an existing LLM configuration."""
    # Fetch existing config
    result = await db.execute(select(LLMConfig).where(LLMConfig.id == model_id))
    db_llm = result.scalar_one_or_none()
    
    if not db_llm:
        raise NotFoundException(resource="LLMConfig", identifier=str(model_id))
    
    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    
    # Handle API key encryption if provided
    if "api_key" in update_dict and update_dict["api_key"]:
        db_llm.api_key_encrypted = encryption_service.encrypt(update_dict.pop("api_key"))
    
    # Update other fields
    for key, value in update_dict.items():
        setattr(db_llm, key, value)
    
    await db.commit()
    await db.refresh(db_llm)
    
    # Re-register in runtime if needed
    await llm_manager.register_model(db_llm)
    
    return message_response(
        message="LLM configuration updated successfully",
        data={"id": db_llm.id}
    )


@router.delete("/{model_id}")
async def delete_llm(
    model_id: int,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """Delete an LLM configuration."""
    # Fetch existing config
    result = await db.execute(select(LLMConfig).where(LLMConfig.id == model_id))
    db_llm = result.scalar_one_or_none()
    
    if not db_llm:
        raise NotFoundException(resource="LLMConfig", identifier=str(model_id))
    
    # Check if it's the active model
    if db_llm.is_default:
        raise BadRequestException(
            message="Cannot delete the currently active model. Please switch to another model first."
        )
    
    # Delete from database
    await db.delete(db_llm)
    await db.commit()
    
    # Remove from runtime registry (sync method, no await needed)
    llm_manager.registry.remove_client(model_id)
    
    return deleted_response(
        resource_id=model_id,
        message="LLM configuration deleted successfully"
    )



