"""
LoRA Model Router

API endpoints for LoRA model management including listing,
training orchestration, and model validation.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List

from app.config.database import get_db_session
from app.models.lora_model import LoRAModel
from app.models.ip_asset import IPAsset
from app.api.deps import get_current_user
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    AppException
)
from app.utils.response import success_response, list_response, created_response, updated_response, deleted_response, message_response
from app.core.lora_trainer import lora_trainer
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/lora", tags=["LoRA Models"])


@router.post("/create", status_code=201)
async def create_lora_model(
    lora_data: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new LoRA model.
    """
    try:
        # Create LoRA model
        new_model = LoRAModel(
            name=lora_data.get("name"),
            base_model=lora_data.get("base_model", "sd1.5"),
            description=lora_data.get("description", ""),
            status="not_trained",
            total_epochs=lora_data.get("epochs", 10),
        )
        
        db.add(new_model)
        await db.commit()
        await db.refresh(new_model)
        
        return created_response(
            data={
                "id": new_model.id,
                "name": new_model.name,
                "base_model": new_model.base_model,
                "status": new_model.status,
                "description": new_model.description,
            },
            message="LoRA model created successfully"
        )
        
    except Exception as e:
        await db.rollback()
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to create LoRA model"
        )


@router.get("/list")
async def list_lora_models(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    ip_asset_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List LoRA models with pagination and filtering.
    """
    try:
        query = select(LoRAModel)
        count_query = select(func.count(LoRAModel.id))
        
        if status:
            query = query.where(LoRAModel.status == status)
            count_query = count_query.where(LoRAModel.status == status)
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(LoRAModel.created_at.desc())
        result = await db.execute(query)
        items = result.scalars().all()
        
        # Fetch associated IP assets
        ip_ids = [lora.id for lora in items if lora.id]
        ip_map = {}
        if ip_ids:
            ip_result = await db.execute(
                select(IPAsset.id, IPAsset.name).where(IPAsset.lora_model_id.in_(ip_ids))
            )
            ip_map = {row[0]: row[1] for row in ip_result.all()}
        
        # Build response
        model_list = []
        for model in items:
            # Find associated IP name
            ip_name = None
            for ip_id, name in ip_map.items():
                if model.id == ip_id:
                    ip_name = name
                    break
            
            model_list.append({
                "id": model.id,
                "name": model.name,
                "base_model": model.base_model,
                "status": model.status,
                "final_loss": model.final_loss,
                "training_steps": model.training_steps,
                "training_time_minutes": model.training_time_minutes,
                "weight_default": model.weight_default,
                "is_active": model.is_active,
                "description": model.description,
                "error_message": model.error_message,
                "ip_name": ip_name,
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "updated_at": model.updated_at.isoformat() if model.updated_at else None,
            })
        
        return list_response(
            items=model_list,
            page=1,
            page_size=total,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Error listing LoRA models: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to list LoRA models: {str(e)}")


@router.get("/{lora_id}")
async def get_lora_model(
    lora_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get a specific LoRA model by ID.
    """
    try:
        result = await db.execute(
            select(LoRAModel).where(LoRAModel.id == lora_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            raise NotFoundException(message=f"LoRA model with ID {lora_id} not found")
        
        # Get associated IP
        ip_result = await db.execute(
            select(IPAsset.id, IPAsset.name).where(IPAsset.lora_model_id == lora_id)
        )
        ip_row = ip_result.first()
        ip_name = ip_row[1] if ip_row else None
        
        return success_response(
            data={
                "id": model.id,
                "name": model.name,
                "file_path": model.file_path,
                "base_model": model.base_model,
                "status": model.status,
                "training_params": model.training_params,
                "final_loss": model.final_loss,
                "training_steps": model.training_steps,
            "training_time_minutes": model.training_time_minutes,
            "weight_default": model.weight_default,
            "is_active": model.is_active,
            "description": model.description,
            "error_message": model.error_message,
            "ip_name": ip_name,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        }
        )
        
    except Exception:
        raise
    except Exception as e:
        logger.error(f"Error getting LoRA model: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to get LoRA model: {str(e)}")


@router.post("/{lora_id}/train")
async def start_training(
    lora_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Start LoRA training for a model.
    """
    try:
        result = await db.execute(
            select(LoRAModel).where(LoRAModel.id == lora_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            raise NotFoundException(message=f"LoRA model with ID {lora_id} not found")
        
        if model.status == "training":
            raise BadRequestException(message="Model is already training")
        
        # Start training
        success = await lora_trainer.start_training(lora_id)
        
        if success:
            return message_response(
                message="Training started"
            )
        else:
            raise AppException(status_code=500, error="ServerError", message="Failed to start training")
            
    except Exception:
        raise
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to start training: {str(e)}")


@router.post("/{lora_id}/cancel")
async def cancel_training(
    lora_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Cancel ongoing LoRA training.
    """
    try:
        success = await lora_trainer.cancel_training(lora_id)
        
        if success:
            return message_response(
                message="Training cancelled"
            )
        else:
            raise BadRequestException(message="Cannot cancel: model is not training")
            
    except Exception:
        raise
    except Exception as e:
        logger.error(f"Error cancelling training: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to cancel training: {str(e)}")


@router.delete("/{lora_id}")
async def delete_lora_model(
    lora_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete a LoRA model.
    """
    try:
        result = await db.execute(
            select(LoRAModel).where(LoRAModel.id == lora_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            raise NotFoundException(message=f"LoRA model with ID {lora_id} not found")
        
        await db.delete(model)
        await db.commit()
        
        logger.info(f"LoRA model '{model.name}' deleted by user {current_user['username']}")
        
        return message_response(
            message="LoRA model deleted"
        )
        
    except Exception:
        raise
    except Exception as e:
        logger.error(f"Error deleting LoRA model: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to delete LoRA model: {str(e)}")


@router.get("/{lora_id}/validate")
async def validate_lora_model(
    lora_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Validate a LoRA model file.
    """
    try:
        result = await lora_trainer.validate_model(lora_id)
        return result
        
    except Exception as e:
        logger.error(f"Error validating LoRA model: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to validate LoRA model: {str(e)}")
