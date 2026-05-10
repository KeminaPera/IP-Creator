"""
Training Dataset Router

API endpoints for training dataset management including
dataset CRUD, image uploads, and quality validation.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.config.database import get_db_session
from app.models.training_dataset import TrainingDataset
from app.schemas.training_dataset import (
    TrainingDatasetCreate,
    TrainingDatasetUpdate,
    TrainingDatasetResponse,
    TrainingDatasetDetail,
    TrainingDatasetListResponse,
    DatasetImageCreate,
    DatasetImageResponse,
    DatasetValidationRequest,
    DatasetValidationReport,
    BatchImageUploadResponse,
    ImageUploadResponse,
)
from app.api.deps import get_current_user
from app.core.dataset_manager import dataset_manager
from app.core.exceptions import NotFoundException, BadRequestException
from app.utils.logger import logger
from app.utils.response import success_response, list_response, created_response, updated_response, deleted_response

router = APIRouter(prefix="/api/v1/datasets", tags=["Training Datasets"])


@router.post("", response_model=TrainingDatasetResponse)
async def create_dataset(
    dataset_data: TrainingDatasetCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new training dataset for an IP asset.
    
    Requires authentication.
    """
    dataset = await dataset_manager.create_dataset(dataset_data, db)
    return created_response(
        data=TrainingDatasetResponse.model_validate(dataset),
        message="Training dataset created successfully"
    )


@router.get("/{dataset_id}", response_model=TrainingDatasetDetail)
async def get_dataset(
    dataset_id: int,
    include_images: bool = False,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get dataset by ID.
    
    Optionally includes images in the response.
    """
    dataset = await dataset_manager.get_dataset(dataset_id, db, include_images)
    return success_response(
        data=TrainingDatasetDetail.model_validate(dataset),
        message="Dataset retrieved successfully"
    )


@router.get("", response_model=TrainingDatasetListResponse)
async def list_datasets(
    ip_asset_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List training datasets with filtering and pagination.
    """
    datasets, total = await dataset_manager.list_datasets(
        db, ip_asset_id, status, skip, limit
    )
    
    # Calculate page (convert from skip/limit to page/page_size)
    page = (skip // limit) + 1 if limit > 0 else 1
    
    return list_response(
        items=[TrainingDatasetResponse.model_validate(d) for d in datasets],
        page=page,
        page_size=limit,
        total=total,
        message="Datasets retrieved successfully"
    )


@router.patch("/{dataset_id}", response_model=TrainingDatasetResponse)
async def update_dataset(
    dataset_id: int,
    dataset_data: TrainingDatasetUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update dataset information.
    """
    dataset = await dataset_manager.update_dataset(dataset_id, dataset_data, db)
    return updated_response(
        data=TrainingDatasetResponse.model_validate(dataset),
        message="Dataset updated successfully"
    )


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete dataset and all associated images.
    """
    await dataset_manager.delete_dataset(dataset_id, db)
    return deleted_response(
        resource_id=dataset_id,
        message="Dataset deleted successfully"
    )


@router.post("/{dataset_id}/images", response_model=DatasetImageResponse)
async def add_image(
    dataset_id: int,
    image_data: DatasetImageCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Add an image to dataset.
    """
    image = await dataset_manager.add_image(dataset_id, image_data, db)
    return created_response(
        data=DatasetImageResponse.model_validate(image),
        message="Image added to dataset successfully"
    )


@router.post("/{dataset_id}/validate", response_model=DatasetValidationReport)
async def validate_dataset(
    dataset_id: int,
    validation_request: DatasetValidationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Validate dataset quality and readiness for training.
    """
    report = await dataset_manager.validate_dataset(dataset_id, db)
    
    # Update dataset status based on validation
    if not report.issues:
        update_data = TrainingDatasetUpdate(
            name=None,  # Will be ignored due to exclude_unset
            status="ready",
            validation_report=report.model_dump()
        )
        await dataset_manager.update_dataset(dataset_id, update_data, db)
    
    return success_response(
        data=report,
        message="Dataset validation completed"
    )


@router.get("/{dataset_id}/stats")
async def get_dataset_stats(
    dataset_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get dataset statistics.
    """
    stats = await dataset_manager.calculate_dataset_stats(dataset_id, db)
    return success_response(data=stats, message="Dataset statistics retrieved")


@router.post("/{dataset_id}/augment")
async def augment_dataset(
    dataset_id: int,
    augmentation_factor: int = 2,
    strategies: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Augment dataset images to increase diversity.
    
    Args:
        dataset_id: Dataset ID
        augmentation_factor: Number of augmented versions per image (default: 2)
        strategies: Specific strategies to apply (default: random)
            Options: horizontal_flip, rotation, brightness, contrast, color_jitter
    """
    result = await dataset_manager.augment_dataset(
        dataset_id, db, augmentation_factor, strategies
    )
    return success_response(
        data=result,
        message=f"Dataset augmentation complete: {result.get('added_to_database', 0)} images added"
    )


@router.post("/{dataset_id}/versions")
async def create_dataset_version(
    dataset_id: int,
    version_note: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a new version of the dataset.
    
    Use this to save the current state before making major changes.
    """
    new_version = await dataset_manager.create_dataset_version(
        dataset_id, db, version_note
    )
    return created_response(
        data=TrainingDatasetResponse.model_validate(new_version),
        message=f"Dataset version {new_version.version} created successfully"
    )
