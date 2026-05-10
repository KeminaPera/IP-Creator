"""
LLM Provider and Model Management Router

Provides standalone API endpoints for managing LLM providers and models.
Path prefix: /api/v1/providers
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.config.database import get_db_session
from app.models.llm_provider import LLMProvider, LLMModel
from app.schemas.llm_schema import (
    LLMProviderCreate, LLMProviderUpdate, LLMProviderResponse,
    LLMModelCreate, LLMModelUpdate, LLMModelResponse,
    ProviderWithModelsResponse
)
from app.services.llm_model_sync import model_sync_service
from app.api.deps import get_current_user, require_admin
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ConflictException,
    AppException
)
from app.utils.logger import logger
from app.utils.response import success_response, created_response, updated_response, deleted_response, message_response

router = APIRouter(prefix="/api/v1/providers", tags=["Provider Management"])


# ========== Provider Endpoints ==========

@router.get("")
@router.get("/")
async def list_providers(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """
    List all providers with their models.
    
    Args:
        include_inactive: Include inactive providers (requires admin)
    
    Returns:
        List of providers with their models
    """
    try:
        # Build query
        query = select(LLMProvider).order_by(LLMProvider.sort_order, LLMProvider.name_en)
        
        if not include_inactive:
            query = query.where(LLMProvider.is_active == True)
        
        result = await db.execute(query)
        providers = result.scalars().all()
        
        # Build response with models
        provider_list = []
        for provider in providers:
            models_result = await db.execute(
                select(LLMModel)
                .where(
                    LLMModel.provider_id == provider.id,
                    LLMModel.is_active == True
                )
                .order_by(LLMModel.sort_order, LLMModel.release_date.desc())
            )
            models = models_result.scalars().all()
            
            provider_list.append(ProviderWithModelsResponse(
                id=provider.id,
                code=provider.code,
                name=provider.name_cn,
                name_cn=provider.name_cn,
                name_en=provider.name_en,
                icon_class=provider.icon_class,
                icon_url=provider.icon_url,
                website=provider.website,
                api_docs_url=provider.api_docs_url,
                default_endpoint=provider.default_endpoint,
                requires_api_key=provider.requires_api_key,
                api_key_pattern=provider.api_key_pattern,
                is_active=provider.is_active,
                is_recommended=provider.is_recommended,
                sort_order=provider.sort_order,
                description_cn=provider.description_cn,
                description_en=provider.description_en,
                last_synced_at=provider.last_synced_at,
                created_at=provider.created_at,
                updated_at=provider.updated_at,
                models=[
                    LLMModelResponse(
                        id=model.id,
                        provider_id=model.provider_id,
                        code=model.code,
                        name=model.name,
                        version=model.version,
                        capabilities=model.capabilities,
                        max_tokens=model.max_tokens,
                        max_output_tokens=model.max_output_tokens,
                        supports_streaming=model.supports_streaming,
                        supports_function_calling=model.supports_function_calling,
                        supports_vision=model.supports_vision,
                        input_price_per_million=model.input_price_per_million,
                        output_price_per_million=model.output_price_per_million,
                        speed_rating=model.speed_rating,
                        quality_rating=model.quality_rating,
                        is_active=model.is_active,
                        is_recommended=model.is_recommended,
                        sort_order=model.sort_order,
                        release_date=model.release_date,
                        deprecated_date=model.deprecated_date,
                        description=model.description,
                        created_at=model.created_at,
                        updated_at=model.updated_at,
                    )
                    for model in models
                ]
            ).model_dump(mode='json', exclude_none=False))
        
        return success_response(data=provider_list)
    
    except Exception as e:
        logger.error(f"Error listing providers: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to list providers: {str(e)}")


@router.get("/all")
async def list_all_providers(
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """List all providers (including inactive). Admin only."""
    try:
        result = await db.execute(
            select(LLMProvider).order_by(LLMProvider.sort_order, LLMProvider.name_en)
        )
        providers = result.scalars().all()
        
        provider_list = [
            LLMProviderResponse(
                id=p.id, code=p.code, name_cn=p.name_cn, name_en=p.name_en,
                icon_class=p.icon_class, icon_url=p.icon_url, website=p.website,
                api_docs_url=p.api_docs_url, default_endpoint=p.default_endpoint,
                requires_api_key=p.requires_api_key, api_key_pattern=p.api_key_pattern,
                is_active=p.is_active, is_recommended=p.is_recommended,
                sort_order=p.sort_order, description_cn=p.description_cn,
                description_en=p.description_en, last_synced_at=p.last_synced_at,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in providers
        ]
        
        return success_response(data=provider_list)
    
    except Exception as e:
        logger.error(f"Error listing all providers: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to list providers: {str(e)}")


@router.post("/", status_code=201)
async def create_provider(
    provider_data: LLMProviderCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """Create a new LLM provider. Admin only."""
    try:
        # Check if code already exists
        existing = await db.execute(
            select(LLMProvider).where(LLMProvider.code == provider_data.code)
        )
        if existing.scalar_one_or_none():
            raise ConflictException(
                message=f"Provider with code '{provider_data.code}' already exists",
                details={"code": provider_data.code}
            )
        
        # Create provider
        provider = LLMProvider(**provider_data.model_dump())
        db.add(provider)
        await db.commit()
        await db.refresh(provider)
        
        logger.info(f"Created provider: {provider.code} by admin {admin['username']}")
        
        return created_response(
            data={
                "id": provider.id, "code": provider.code, "name_cn": provider.name_cn,
                "name_en": provider.name_en, "icon_class": provider.icon_class,
                "icon_url": provider.icon_url, "website": provider.website,
                "api_docs_url": provider.api_docs_url, "default_endpoint": provider.default_endpoint,
                "requires_api_key": provider.requires_api_key, "api_key_pattern": provider.api_key_pattern,
                "is_active": provider.is_active, "is_recommended": provider.is_recommended,
                "sort_order": provider.sort_order, "description_cn": provider.description_cn,
                "description_en": provider.description_en, "last_synced_at": provider.last_synced_at,
                "created_at": provider.created_at,
                "updated_at": provider.updated_at
            },
            message="Provider created successfully"
        )
    
    except Exception:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating provider: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to create provider: {str(e)}")


@router.put("/{provider_id}")
async def update_provider(
    provider_id: int,
    provider_data: LLMProviderUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """Update an LLM provider. Admin only."""
    try:
        # Fetch provider
        result = await db.execute(
            select(LLMProvider).where(LLMProvider.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        
        if not provider:
            raise NotFoundException(resource="Provider", identifier=str(provider_id))
        
        # Update fields
        update_data = provider_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(provider, field, value)
        
        await db.commit()
        await db.refresh(provider)
        
        logger.info(f"Updated provider: {provider.code} by admin {admin['username']}")
        
        return updated_response(
            data={
                "id": provider.id, "code": provider.code, "name_cn": provider.name_cn,
                "name_en": provider.name_en
            },
            message="Provider updated successfully"
        )
    
    except Exception:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating provider: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to update provider: {str(e)}")


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """Delete an LLM provider and all its models. Admin only."""
    try:
        result = await db.execute(
            select(LLMProvider).where(LLMProvider.id == provider_id)
        )
        provider = result.scalar_one_or_none()
        
        if not provider:
            raise NotFoundException(resource="Provider", identifier=str(provider_id))
        
        await db.delete(provider)
        await db.commit()
        
        logger.info(f"Deleted provider: {provider.code} by admin {admin['username']}")
        
        return message_response(message="Provider deleted successfully")
    
    except Exception:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting provider: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to delete provider: {str(e)}")


# ========== Model Endpoints ==========

@router.get("/models")
async def list_all_models(
    provider_id: Optional[int] = None,
    capability: Optional[str] = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """
    List all models across all providers.
    
    Args:
        provider_id: Filter by provider ID
        capability: Filter by capability (e.g., 'text_generation', 'vision')
        include_inactive: Include inactive models
    
    Returns:
        List of models
    """
    try:
        # Build query
        query = select(LLMModel)
        
        if provider_id:
            query = query.where(LLMModel.provider_id == provider_id)
        
        if not include_inactive:
            query = query.where(LLMModel.is_active == True)
        
        query = query.order_by(LLMModel.sort_order, LLMModel.release_date.desc())
        
        result = await db.execute(query)
        models = result.scalars().all()
        
        # Filter by capability if specified
        if capability:
            models = [
                m for m in models
                if m.capabilities and capability in m.capabilities
            ]
        
        model_list = [
            LLMModelResponse(
                id=m.id, provider_id=m.provider_id, code=m.code, name=m.name,
                version=m.version, capabilities=m.capabilities, max_tokens=m.max_tokens,
                max_output_tokens=m.max_output_tokens, supports_streaming=m.supports_streaming,
                supports_function_calling=m.supports_function_calling,
                supports_vision=m.supports_vision,
                input_price_per_million=m.input_price_per_million,
                output_price_per_million=m.output_price_per_million,
                speed_rating=m.speed_rating, quality_rating=m.quality_rating,
                is_active=m.is_active, is_recommended=m.is_recommended,
                sort_order=m.sort_order, release_date=m.release_date,
                deprecated_date=m.deprecated_date, description=m.description,
                created_at=m.created_at, updated_at=m.updated_at
            )
            for m in models
        ]
        
        return success_response(data=model_list)
    
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to list models: {str(e)}")


@router.post("/models", status_code=201)
async def create_model(
    model_data: LLMModelCreate,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """Create a new LLM model. Admin only."""
    try:
        # Verify provider exists
        provider_result = await db.execute(
            select(LLMProvider).where(LLMProvider.id == model_data.provider_id)
        )
        if not provider_result.scalar_one_or_none():
            raise NotFoundException(resource="Provider", identifier=str(model_data.provider_id))
        
        # Check if model code already exists for this provider
        existing = await db.execute(
            select(LLMModel).where(
                LLMModel.provider_id == model_data.provider_id,
                LLMModel.code == model_data.code
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictException(
                message=f"Model with code '{model_data.code}' already exists for this provider",
                details={"provider_id": model_data.provider_id, "code": model_data.code}
            )
        
        # Create model
        model = LLMModel(**model_data.model_dump())
        db.add(model)
        await db.commit()
        await db.refresh(model)
        
        logger.info(f"Created model: {model.code} by admin {admin['username']}")
        
        return created_response(
            data={"id": model.id, "code": model.code, "name": model.name},
            message="Model created successfully"
        )
    
    except Exception:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating model: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to create model: {str(e)}")


@router.put("/models/{model_id}")
async def update_model(
    model_id: int,
    model_data: LLMModelUpdate,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """Update an LLM model. Admin only."""
    try:
        result = await db.execute(
            select(LLMModel).where(LLMModel.id == model_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            raise NotFoundException(resource="Model", identifier=str(model_id))
        
        # Update fields
        update_data = model_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(model, field, value)
        
        await db.commit()
        await db.refresh(model)
        
        logger.info(f"Updated model: {model.code} by admin {admin['username']}")
        
        return updated_response(
            data={"id": model.id, "code": model.code, "name": model.name},
            message="Model updated successfully"
        )
    
    except Exception:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating model: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to update model: {str(e)}")


@router.delete("/models/{model_id}", status_code=204)
async def delete_model(
    model_id: int,
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """Delete an LLM model. Admin only."""
    try:
        result = await db.execute(
            select(LLMModel).where(LLMModel.id == model_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            raise NotFoundException(resource="Model", identifier=str(model_id))
        
        await db.delete(model)
        await db.commit()
        
        logger.info(f"Deleted model: {model.code} by admin {admin['username']}")
        
        return message_response(message="Model deleted successfully")
    
    except Exception:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting model: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to delete model: {str(e)}")


# ========== Provider Model Sync Endpoints ==========

@router.post("/{provider_code}/sync-models")
async def sync_provider_models(
    provider_code: str,
    request_data: dict = {},
    db: AsyncSession = Depends(get_db_session),
    admin: dict = Depends(require_admin),
):
    """
    Synchronize models from a provider's official API.
    
    This endpoint fetches the latest model information from the provider
    and updates the database with new models or updates existing ones.
    
    Args:
        provider_code: Provider identifier (e.g., 'openai', 'google')
        request_data: Optional request body with api_key
    """
    api_key = request_data.get("api_key")
    
    try:
        result = await model_sync_service.sync_provider_models(
            db=db,
            provider_code=provider_code,
            api_key=api_key,
        )
        
        return success_response(
            data=result,
            message="Models synced successfully"
        )
        
    except ValueError as e:
        raise BadRequestException(message=str(e))
    except Exception as e:
        raise AppException(
            status_code=500,
            error="ModelSyncError",
            message=f"Failed to sync models for {provider_code}"
        )
