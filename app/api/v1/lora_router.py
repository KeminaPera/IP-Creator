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
from app.models.training_dataset import TrainingDataset
from app.api.deps import get_current_user
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    AppException
)
from app.utils.response import success_response, list_response, created_response, updated_response, deleted_response, message_response
from app.core.lora_trainer import lora_trainer
from app.utils.logger import logger
from app.schemas.training_config import (
    LoRATrainingConfig,
    TrainingConfigResponse,
    StartTrainingRequest,
    list_presets,
    get_preset,
    estimate_training_time
)
from app.services.training_logger import training_logger
from app.services.dataset_converter import DatasetConverter
from app.services.kohya_detector import KohyaDetector
from app.services.quality_assessor import QualityAssessor

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
        from pathlib import Path
        from app.config.settings import settings
        
        # Generate default file path
        output_path = Path(settings.LORA_MODELS_PATH) / f"{lora_data.get('name')}.safetensors"
        
        # Create LoRA model
        new_model = LoRAModel(
            name=lora_data.get("name"),
            file_path=str(output_path),
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
        
        # Fetch latest quality reports for each LoRA model
        from app.models.quality_report import QualityReport
        quality_map = {}
        if ip_ids:
            # Get the latest quality report for each lora_id
            quality_result = await db.execute(
                select(QualityReport.lora_id, QualityReport.grade, QualityReport.overall_score)
                .where(QualityReport.lora_id.in_(ip_ids))
                .order_by(QualityReport.lora_id, QualityReport.created_at.desc())
            )
            # Keep only the latest report for each lora_id
            for row in quality_result.all():
                if row[0] not in quality_map:  # First one is the latest due to desc order
                    quality_map[row[0]] = {"grade": row[1], "score": row[2]}
        
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
                "quality_grade": quality_map.get(model.id, {}).get("grade"),
                "quality_score": quality_map.get(model.id, {}).get("score"),
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
        raise AppException(status_code=500, error="ServerError", message=f"Failed to list LoRA models: {str(e)}")


@router.get("/presets")
async def get_training_presets(
    current_user: dict = Depends(get_current_user),
):
    """
    Get all available training presets.
    """
    try:
        presets = list_presets()
        
        return success_response(
            data=[p.model_dump() for p in presets],
            message="Training presets retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting training presets: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to get training presets")


@router.post("/validate-config")
async def validate_training_config(
    config: LoRATrainingConfig,
    current_user: dict = Depends(get_current_user),
):
    """
    Validate training configuration and provide recommendations.
    """
    try:
        # Estimate training time
        estimated_time = estimate_training_time(config)
        
        # Generate recommendations
        recommendations = []
        
        if config.epochs < 5:
            recommendations.append("Consider using at least 5 epochs for better results")
        
        if config.learning_rate > 5e-4:
            recommendations.append("High learning rate may cause instability")
        
        if config.network_dim < 32:
            recommendations.append("Low network dimension may limit model capacity")
        
        if config.resolution > 768 and config.batch_size > 1:
            recommendations.append("High resolution with large batch size requires significant VRAM")
        
        return success_response(
            data={
                "valid": True,
                "estimated_time_minutes": estimated_time,
                "recommendations": recommendations,
                "config": config.model_dump(),
            },
            message="Training configuration is valid"
        )
    except Exception as e:
        logger.error(f"Error validating training config: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to validate configuration")


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
        
    except Exception as e:
        logger.error(f"Error getting LoRA model: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to get LoRA model: {str(e)}")


@router.post("/{lora_id}/cancel")
async def cancel_training(
    lora_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Cancel LoRA training for a model.
    """
    try:
        success = await lora_trainer.cancel_training(lora_id)
        
        if success:
            return message_response(message="Training cancelled")
        else:
            raise BadRequestException(message="Cannot cancel training")
            
    except Exception as e:
        logger.error(f"Error cancelling training: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to cancel training")


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
        
    except Exception as e:
        logger.error(f"Error deleting LoRA model: {e}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to delete LoRA model: {str(e)}")


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
        raise AppException(status_code=500, error="ServerError", message=f"Failed to validate LoRA model: {str(e)}")


@router.post("/{lora_id}/train")
async def start_training(
    lora_id: int,
    request: StartTrainingRequest = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Start training for a LoRA model.
    
    Supports:
    - Using preset configuration
    - Custom configuration
    - Dataset association (automatic conversion to Kohya format)
    - Default configuration (no request body)
    """
    try:
        # Check if model exists
        result = await db.execute(
            select(LoRAModel).where(LoRAModel.id == lora_id)
        )
        lora_model = result.scalar_one_or_none()
        
        if not lora_model:
            raise NotFoundException(resource="LoRA model", identifier=str(lora_id))
        
        if lora_model.status == "training":
            raise BadRequestException("Model is already training")
        
        # Apply configuration if provided
        config_applied = False
        config_info = {}
        dataset_info = {}
        
        if request:
            if request.use_preset:
                # Apply preset configuration
                preset = get_preset(request.use_preset)
                if preset:
                    config_info = {
                        "preset": preset.name,
                        "preset_display_name": preset.display_name,
                        "description": preset.description
                    }
                    config_applied = True
                    logger.info(f"Applied preset '{preset.display_name}' for LoRA {lora_id}")
            
            if request.custom_config:
                # Validate and apply custom configuration
                config_info = {
                    "custom": True,
                    "epochs": request.custom_config.epochs,
                    "learning_rate": request.custom_config.learning_rate,
                    "network_dim": request.custom_config.network_dim,
                    "estimated_time_minutes": estimate_training_time(request.custom_config)
                }
                config_applied = True
                logger.info(f"Applied custom configuration for LoRA {lora_id}")
        
        # Handle dataset association and conversion
        if lora_model.dataset_id:
            # Load dataset
            dataset = await db.get(TrainingDataset, lora_model.dataset_id)
            if dataset:
                dataset_info = {
                    "dataset_id": dataset.id,
                    "dataset_name": dataset.name,
                    "image_count": dataset.image_count,
                }
                
                # Convert to Kohya format if not already done
                converter = DatasetConverter()
                from pathlib import Path
                from app.config.settings import settings
                kohya_dir = Path(settings.STORAGE_PATH) / "datasets" / f"kohya_dataset_{dataset.id}"
                
                if not kohya_dir.exists():
                    logger.info(f"Converting dataset {dataset.id} to Kohya format")
                    conversion_result = await converter.convert_to_kohya_format(
                        dataset_id=dataset.id
                    )
                    dataset_info["kohya_directory"] = conversion_result["kohya_directory"]
                    dataset_info["converted_images"] = conversion_result["converted_images"]
                else:
                    dataset_info["kohya_directory"] = str(kohya_dir)
                    dataset_info["already_converted"] = True
                
                logger.info(f"Dataset associated: {dataset.name} with {dataset.image_count} images")
        
        # Start training in background
        import asyncio
        asyncio.create_task(lora_trainer.start_training(lora_id))
        
        response_data = {
            "lora_id": lora_id,
            "status": "training_started",
            "config_applied": config_applied
        }
        
        if config_info:
            response_data["config"] = config_info
        
        if dataset_info:
            response_data["dataset"] = dataset_info
        
        return success_response(
            data=response_data,
            message="Training started successfully"
        )
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to start training")


@router.get("/{lora_id}/logs")
async def get_training_logs(
    lora_id: int,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """
    Get training logs for a LoRA model.
    """
    try:
        logs = await training_logger.get_logs(lora_id, limit, offset)
        
        return success_response(
            data={"logs": logs, "count": len(logs)},
            message="Training logs retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting training logs: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to get training logs")


@router.get("/{lora_id}/metrics")
async def get_training_metrics(
    lora_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Get training metrics (loss curve, learning rate, etc.).
    """
    try:
        metrics = await training_logger.get_metrics(lora_id)
        
        return success_response(
            data=metrics,
            message="Training metrics retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting training metrics: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to get training metrics")


# ============================================
# Kohya Environment Detection
# ============================================

@router.get("/check-kohya")
async def check_kohya_environment(
    current_user: dict = Depends(get_current_user),
):
    """
    Check Kohya-ss environment installation and readiness.
    
    Returns:
    - Installation status
    - GPU availability
    - Required packages
    - Recommendations
    """
    try:
        detector = KohyaDetector()
        validation = detector.validate_environment()
        
        return success_response(
            data=validation,
            message="Environment check completed"
        )
    except Exception as e:
        logger.error(f"Error checking Kohya environment: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to check environment")


# ============================================
# Quality Assessment
# ============================================

@router.post("/{lora_id}/assess-quality")
async def assess_model_quality(
    lora_id: int,
    request: Optional[dict] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Assess LoRA model quality after training completion.
    
    Generates test images, calculates quality scores,
    and creates comprehensive quality report.
    """
    try:
        # Check if model exists and is completed
        result = await db.execute(
            select(LoRAModel).where(LoRAModel.id == lora_id)
        )
        lora_model = result.scalar_one_or_none()
        
        if not lora_model:
            raise NotFoundException(resource="LoRA model", identifier=str(lora_id))
        
        if lora_model.status != "completed":
            raise BadRequestException(f"Model must be completed before assessment (current: {lora_model.status})")
        
        # Get parameters
        num_images = 5
        if request:
            num_images = request.get("num_test_images", 5)
        
        # Run quality assessment
        assessor = QualityAssessor()
        assessment = await assessor.assess_model_quality(
            lora_id=lora_id,
            num_test_images=num_images,
        )
        
        return success_response(
            data=assessment,
            message=f"Quality assessment completed: {assessment['overall_score']}/100 ({assessment['grade']})"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Error assessing quality: {e}")
        raise AppException(status_code=500, error="ServerError", message="Failed to assess quality")


@router.get("/{lora_id}/quality-report")
async def get_quality_report(
    lora_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get quality report for a LoRA model.
    """
    try:
        from app.models.quality_report import QualityReport
        import traceback
        
        logger.info(f"Getting quality report for LoRA model {lora_id}")
        
        # Get latest report
        result = await db.execute(
            select(QualityReport)
            .where(QualityReport.lora_id == lora_id)
            .order_by(QualityReport.created_at.desc())
            .limit(1)
        )
        report = result.scalar_one_or_none()
        
        if not report:
            logger.info(f"No quality report found for LoRA model {lora_id}")
            raise NotFoundException(resource="Quality report", identifier=f"for LoRA model {lora_id}")
        
        logger.info(f"Quality report found: score={report.overall_score}, grade={report.grade}")
        
        return success_response(
            data={
                "id": report.id,
                "overall_score": report.overall_score,
                "grade": report.grade,
                "loss_score": report.loss_score,
                "completion_score": report.completion_score,
                "file_score": report.file_score,
                "generation_success": report.generation_success,
                "clip_consistency": report.clip_consistency,
                "test_images": report.test_images,
                "recommendations": report.recommendations,
                "training_diagnosis": report.training_diagnosis,
                "created_at": report.created_at.isoformat() if report.created_at else None,
            },
            message="Quality report retrieved successfully"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Error getting quality report: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise AppException(status_code=500, error="ServerError", message=f"Failed to get quality report: {str(e)}")
