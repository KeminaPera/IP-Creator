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
from app.models.dataset_image import DatasetImage
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
from app.utils.caption_generator import generate_caption_from_annotation, generate_caption_batch
from app.config.feature_types import FEATURE_TYPE_CONFIG
from app.services.dataset_generator import DatasetGenerator
from app.services.dataset_converter import DatasetConverter

router = APIRouter(prefix="/api/v1/datasets", tags=["Training Datasets"])


@router.post("", status_code=201)
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


@router.get("/{dataset_id}")
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


@router.get("")
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
    
    return list_response(
        items=[TrainingDatasetResponse.model_validate(d) for d in datasets],
        page=(skip // limit) + 1 if limit > 0 else 1,
        page_size=limit,
        total=total
    )


@router.patch("/{dataset_id}")
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


@router.post("/{dataset_id}/images", status_code=201)
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


@router.post("/{dataset_id}/generate-captions")
async def generate_captions(
    dataset_id: int,
    trigger_word: str = Form(...),
    use_ai: bool = Form(False),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate captions for all images in dataset.
    
    Uses fixed template + annotations to generate consistent captions.
    
    Args:
        dataset_id: Dataset ID
        trigger_word: IP trigger word (e.g., "xiao_huli_character")
        use_ai: Whether to use AI enhancement (not implemented yet)
    """
    # Get all images in dataset
    result = await db.execute(
        select(TrainingDataset).where(TrainingDataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise NotFoundException(f"Dataset {dataset_id} not found")
    
    # Load images with annotations
    images_result = await db.execute(
        select(DatasetImage).where(
            DatasetImage.dataset_id == dataset_id,
            DatasetImage.is_selected == True
        )
    )
    images = images_result.scalars().all()
    
    # Generate captions
    updated_count = 0
    captions = []
    
    for image in images:
        # Build features dict from annotations
        features = {}
        if image.expression:
            features["expression"] = image.expression
        if image.pose:
            features["pose"] = image.pose
        
        # Generate caption
        caption = generate_caption_from_annotation(
            trigger_word=trigger_word,
            angle=image.angle or "front",
            pose=image.pose,
            background=image.background,
            features=features
        )
        
        # Store caption (you can add a caption field to DatasetImage if needed)
        # For now, we return the generated captions
        captions.append({
            "image_id": image.id,
            "file_path": image.file_path,
            "caption": caption
        })
        updated_count += 1
    
    return success_response(
        data={
            "dataset_id": dataset_id,
            "trigger_word": trigger_word,
            "captions": captions,
            "total_generated": updated_count
        },
        message=f"Generated {updated_count} captions successfully"
    )


@router.post("/{dataset_id}/batch-annotate")
async def batch_annotate_images(
    dataset_id: int,
    annotations: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Batch annotate multiple images in dataset.
    
    Args:
        dataset_id: Dataset ID
        annotations: Dict of {image_id: {angle, expression, pose, background}}
    """
    updated_count = 0
    
    for image_id, annotation in annotations.items():
        result = await db.execute(
            select(DatasetImage).where(
                DatasetImage.id == int(image_id),
                DatasetImage.dataset_id == dataset_id
            )
        )
        image = result.scalar_one_or_none()
        
        if image:
            # Update annotations
            if "angle" in annotation:
                image.angle = annotation["angle"]
            if "expression" in annotation:
                image.expression = annotation["expression"]
            if "pose" in annotation:
                image.pose = annotation["pose"]
            if "background" in annotation:
                image.background = annotation["background"]
            
            updated_count += 1
    
    await db.commit()
    
    return success_response(
        data={"updated_count": updated_count},
        message=f"Updated {updated_count} images successfully"
    )


# ============================================
# Dataset Generation from Features
# ============================================

@router.post("/generate-from-features")
async def generate_dataset_from_features(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate training dataset from IP feature library.
    
    Request body:
    {
        "ip_asset_id": 1,
        "selected_features": {
            "outfit": [1, 2],
            "expression": [3, 4, 5],
            "pose": [6, 7]
        },
        "dataset_name": "小狐狸 - 完整训练集",
        "description": "包含2种服装、3种表情、2种动作"
    }
    """
    try:
        ip_asset_id = request.get("ip_asset_id")
        selected_features = request.get("selected_features", {})
        dataset_name = request.get("dataset_name")
        description = request.get("description", "")
        
        if not ip_asset_id or not dataset_name:
            raise BadRequestException("ip_asset_id and dataset_name are required")
        
        if not selected_features:
            raise BadRequestException("selected_features cannot be empty")
        
        # Generate dataset
        generator = DatasetGenerator(db)
        dataset = await generator.generate_dataset_from_features(
            ip_asset_id=ip_asset_id,
            selected_features=selected_features,
            dataset_name=dataset_name,
            description=description,
        )
        
        return created_response(
            data={
                "id": dataset.id,
                "name": dataset.name,
                "image_count": dataset.image_count,
                "status": dataset.status,
            },
            message=f"Dataset created with {dataset.image_count} images"
        )
        
    except (BadRequestException, NotFoundException):
        raise
    except Exception as e:
        logger.error(f"Error generating dataset: {e}")
        raise BadRequestException(f"Failed to generate dataset: {str(e)}")


@router.post("/preview-combinations")
async def preview_dataset_combinations(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Preview dataset combinations without creating dataset.
    
    Request body:
    {
        "ip_asset_id": 1,
        "selected_features": {
            "outfit": [1, 2],
            "expression": [3, 4, 5]
        }
    }
    """
    try:
        ip_asset_id = request.get("ip_asset_id")
        selected_features = request.get("selected_features", {})
        
        if not ip_asset_id or not selected_features:
            raise BadRequestException("ip_asset_id and selected_features are required")
        
        generator = DatasetGenerator(db)
        preview = await generator.preview_combinations(
            ip_asset_id=ip_asset_id,
            selected_features=selected_features,
        )
        
        return success_response(
            data=preview,
            message="Preview generated successfully"
        )
        
    except (BadRequestException, NotFoundException):
        raise
    except Exception as e:
        logger.error(f"Error previewing combinations: {e}")
        raise BadRequestException(f"Failed to preview: {str(e)}")


@router.post("/{dataset_id}/convert-to-kohya")
async def convert_dataset_to_kohya(
    dataset_id: int,
    request: Optional[dict] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Convert dataset to Kohya-sd training format.
    
    Creates:
    - Image files in kohya directory
    - Caption .txt files for each image
    - metadata.json with dataset info
    """
    try:
        output_dir = request.get("output_dir") if request else None
        
        converter = DatasetConverter()
        result = await converter.convert_to_kohya_format(
            dataset_id=dataset_id,
            output_dir=output_dir,
        )
        
        return success_response(
            data=result,
            message=f"Converted {result['converted_images']} images to Kohya format"
        )
        
    except (BadRequestException, NotFoundException, ValueError) as e:
        raise BadRequestException(str(e))
    except Exception as e:
        logger.error(f"Error converting dataset: {e}")
        raise BadRequestException(f"Failed to convert dataset: {str(e)}")


@router.post("/{dataset_id}/validate-kohya")
async def validate_kohya_dataset(
    dataset_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Validate a Kohya dataset directory.
    
    Checks:
    - Image files exist
    - Caption files match images
    - Caption content is valid
    """
    try:
        # Get dataset
        dataset = await db.get(TrainingDataset, dataset_id)
        if not dataset:
            raise NotFoundException(f"Dataset {dataset_id} not found")
        
        # Find kohya directory (assume it's in storage path)
        from pathlib import Path
        from app.config.settings import settings
        kohya_dir = Path(settings.STORAGE_PATH) / "datasets" / f"kohya_dataset_{dataset_id}"
        
        if not kohya_dir.exists():
            raise BadRequestException(f"Kohya directory not found. Please convert the dataset first.")
        
        converter = DatasetConverter()
        validation = await converter.validate_kohya_dataset(str(kohya_dir))
        
        return success_response(
            data=validation,
            message="Validation completed"
        )
        
    except (BadRequestException, NotFoundException):
        raise
    except Exception as e:
        logger.error(f"Error validating dataset: {e}")
        raise BadRequestException(f"Failed to validate: {str(e)}")

