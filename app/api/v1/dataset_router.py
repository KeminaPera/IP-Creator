"""
Training Dataset Router

API endpoints for training dataset management including
dataset CRUD, image uploads, and quality validation.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

from app.config.database import get_db_session
from app.models.training_dataset import TrainingDataset
from app.models.dataset_image import DatasetImage
from app.models.ip_asset import IPAsset
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
    DatasetGenerationRequest,
    DatasetPreviewRequest,
    DatasetConversionRequest,
    DatasetAugmentationRequest,
    AugmentationValidationRequest,
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
from app.services.data_augmentation import DataAugmentation

router = APIRouter(prefix="/api/v1/datasets", tags=["Training Datasets"])


# Request schemas
class QualityFilterRequest(BaseModel):
    """Request schema for filtering low quality images."""
    threshold: float = Field(default=30.0, ge=0.0, le=100.0, description="Quality score threshold")
    action: Literal["mark", "delete"] = Field(default="mark", description="Action to take: mark or delete")


class BatchAnnotateRequest(BaseModel):
    """Request schema for batch annotating images."""
    image_ids: List[int] = Field(..., min_items=1, description="List of image IDs")
    updates: dict = Field(..., min_items=1, description="Annotation updates")


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
    
    # Use different schema based on include_images flag
    if include_images:
        return success_response(
            data=TrainingDatasetDetail.model_validate(dataset),
            message="Dataset retrieved successfully"
        )
    else:
        return success_response(
            data=TrainingDatasetResponse.model_validate(dataset),
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


@router.post("/{dataset_id}/upload-images", status_code=201)
async def upload_images(
    dataset_id: int,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Upload multiple images to dataset.
    
    Args:
        dataset_id: Dataset ID
        files: List of image files to upload
    
    Returns:
        Upload result with image count and paths
    """
    from pathlib import Path
    from app.config.settings import settings
    from PIL import Image
    import io
    import uuid
    import re
    
    try:
        # Check if dataset exists
        result = await db.execute(
            select(TrainingDataset).where(TrainingDataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        
        if not dataset:
            raise NotFoundException(resource="Dataset", identifier=str(dataset_id))
        
        # Validate file count
        if len(files) > settings.MAX_UPLOAD_FILES:
            raise BadRequestException(
                f"Too many files: {len(files)}. Maximum allowed: {settings.MAX_UPLOAD_FILES}"
            )
        
        # Create upload directory
        upload_dir = Path(settings.STORAGE_PATH) / "datasets" / f"dataset_{dataset_id}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_images = []
        skipped_count = 0
        saved_files = []  # Track saved files for cleanup on failure
        failed_files = []  # Track detailed failure information
        
        # Process each file
        for file in files:
            file_path = None
            try:
                # Check MIME type
                if not file.content_type or file.content_type not in settings.ALLOWED_MIME_TYPES:
                    logger.warning(f"Skipping file with invalid MIME type: {file.filename} ({file.content_type})")
                    failed_files.append({
                        "filename": file.filename,
                        "error": f"Invalid file type: {file.content_type or 'unknown'}"
                    })
                    skipped_count += 1
                    continue
                
                # Sanitize and validate file extension
                if file.filename:
                    file_extension = Path(file.filename).suffix.lower()
                    # Validate extension is safe
                    if not re.match(r'^\.(jpg|jpeg|png|webp)$', file_extension):
                        file_extension = '.jpg'
                else:
                    file_extension = '.jpg'
                
                # Generate unique filename
                unique_filename = f"{uuid.uuid4().hex}{file_extension}"
                file_path = upload_dir / unique_filename
                
                # Read file content
                content = await file.read()
                
                # Check file size BEFORE saving
                if len(content) > settings.MAX_UPLOAD_SIZE:
                    logger.warning(f"File {file.filename} exceeds size limit: {len(content)} bytes")
                    failed_files.append({
                        "filename": file.filename,
                        "error": f"File too large: {len(content) / 1024 / 1024:.1f}MB (max: {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.0f}MB)"
                    })
                    skipped_count += 1
                    continue
                
                # Validate actual image content (not just MIME type)
                try:
                    img = Image.open(io.BytesIO(content))
                    img.verify()  # Verify it's a valid, non-corrupted image
                    
                    # Re-open after verify() as it closes the image
                    img = Image.open(io.BytesIO(content))
                    width, height = img.size
                    
                    # Validate dimensions
                    if width < settings.MIN_IMAGE_DIMENSION or height < settings.MIN_IMAGE_DIMENSION:
                        logger.warning(f"Image {file.filename} too small: {width}x{height}")
                        failed_files.append({
                            "filename": file.filename,
                            "error": f"Image too small: {width}x{height} (min: {settings.MIN_IMAGE_DIMENSION}px)"
                        })
                        skipped_count += 1
                        continue
                    
                    if width > settings.MAX_IMAGE_DIMENSION or height > settings.MAX_IMAGE_DIMENSION:
                        logger.warning(f"Image {file.filename} too large: {width}x{height}")
                        failed_files.append({
                            "filename": file.filename,
                            "error": f"Image too large: {width}x{height} (max: {settings.MAX_IMAGE_DIMENSION}px)"
                        })
                        skipped_count += 1
                        continue
                        
                except Exception as img_error:
                    logger.warning(f"Invalid or corrupted image file {file.filename}: {img_error}")
                    failed_files.append({
                        "filename": file.filename,
                        "error": f"Invalid image file: {str(img_error)}"
                    })
                    skipped_count += 1
                    continue
                
                # Save file to disk
                with open(file_path, 'wb') as f:
                    f.write(content)
                saved_files.append(file_path)  # Track for potential cleanup
                
                # Evaluate image quality automatically
                from app.core.dataset_manager import dataset_manager
                quality_score = await dataset_manager.evaluate_image_quality(str(file_path))
                
                # Create dataset image record with correct schema fields
                dataset_image = DatasetImage(
                    dataset_id=dataset_id,
                    file_path=str(file_path),
                    width=width,
                    height=height,
                    file_size_kb=len(content) // 1024,
                    quality_score=quality_score,
                    angle="unknown",
                    expression="unknown",
                    pose="unknown",
                )
                
                db.add(dataset_image)
                uploaded_images.append({
                    "filename": file.filename,
                    "path": str(file_path),
                    "size": len(content),
                    "width": width,
                    "height": height,
                })
                
            except BadRequestException:
                # Re-raise validation errors
                raise
            except Exception as e:
                logger.error(f"Failed to upload file {file.filename}: {e}")
                failed_files.append({
                    "filename": file.filename,
                    "error": str(e)
                })
                skipped_count += 1
                # Clean up this specific file if it was saved
                if file_path and file_path.exists():
                    try:
                        file_path.unlink()
                        saved_files.remove(file_path)
                        logger.info(f"Cleaned up failed file: {file_path}")
                    except Exception as cleanup_error:
                        logger.error(f"Failed to cleanup file {file_path}: {cleanup_error}")
                continue
        
        # Check if any files were successfully uploaded
        if len(uploaded_images) == 0:
            raise BadRequestException(
                f"No valid images were uploaded. All {len(files)} files failed validation."
            )
        
        # Update dataset image count (add to existing count, not replace)
        dataset.image_count = (dataset.image_count or 0) + len(uploaded_images)
        
        # Commit to database
        await db.commit()
        
        return created_response(
            data={
                "uploaded_count": len(uploaded_images),
                "skipped_count": skipped_count,
                "images": uploaded_images,
                "failed_files": failed_files if failed_files else None,
            },
            message=f"Successfully uploaded {len(uploaded_images)} images"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        # Rollback database changes
        await db.rollback()
        
        # Clean up all saved files to prevent orphans
        for saved_file in saved_files:
            if saved_file.exists():
                try:
                    saved_file.unlink()
                    logger.warning(f"Cleaned up orphaned file during rollback: {saved_file}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup orphaned file {saved_file}: {cleanup_error}")
        
        logger.error(f"Error uploading images: {e}")
        raise BadRequestException(f"Failed to upload images: {str(e)}")


@router.post("/{dataset_id}/validate")
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


@router.post("/{dataset_id}/evaluate-quality")
async def evaluate_dataset_quality(
    dataset_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Batch evaluate quality for all images in dataset."""
    result = await dataset_manager.batch_evaluate_quality(dataset_id, db)
    return success_response(
        data=result,
        message=f"质量评估完成：{result['evaluated']}/{result['total']} 张图片，平均分 {result['average_quality']}"
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


@router.get("/{dataset_id}/quality-distribution")
async def get_quality_distribution(
    dataset_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get quality score distribution for dataset images."""
    distribution = await dataset_manager.get_quality_distribution(dataset_id, db)
    return success_response(data=distribution, message="Quality distribution retrieved")


class DatasetAugmentRequest(BaseModel):
    """Request schema for dataset augmentation."""
    augmentation_factor: int = Field(default=2, ge=1, le=5, description="Augmentation factor (1-5)")
    strategies: Optional[List[str]] = Field(
        default=None,
        description="Augmentation strategies: horizontal_flip, rotation, brightness, contrast, color_jitter"
    )


@router.post("/{dataset_id}/augment")
async def augment_dataset(
    dataset_id: int,
    augment_request: DatasetAugmentRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Augment dataset images to increase diversity.
    
    Args:
        dataset_id: Dataset ID
        augment_request: Augment request body with factor and strategies
    """
    result = await dataset_manager.augment_dataset(
        dataset_id, db, augment_request.augmentation_factor, augment_request.strategies
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
        raise NotFoundException(resource="Dataset", identifier=str(dataset_id))
    
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


@router.post("/{dataset_id}/filter-quality")
async def filter_low_quality_images(
    dataset_id: int,
    request: QualityFilterRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Filter and optionally delete low quality images.
    
    Request body:
    {
        "threshold": 30.0,  # Quality score threshold
        "action": "mark" or "delete"  # Mark as unselected or delete
    }
    """
    try:
        threshold = request.threshold
        action = request.action
        
        # Get low quality images
        result = await db.execute(
            select(DatasetImage).where(
                and_(
                    DatasetImage.dataset_id == dataset_id,
                    DatasetImage.quality_score.isnot(None),
                    DatasetImage.quality_score < threshold,
                    DatasetImage.is_selected == True
                )
            )
        )
        low_quality_images = result.scalars().all()
        
        if not low_quality_images:
            return success_response(
                data={"affected_count": 0},
                message=f"No images found with quality score below {threshold}"
            )
        
        affected_count = 0
        
        if action == "delete":
            # Delete images and files
            for image in low_quality_images:
                # Delete file
                try:
                    from pathlib import Path
                    file_path = Path(image.file_path)
                    if file_path.exists():
                        file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete file {image.file_path}: {e}")
                
                # Delete database record
                await db.delete(image)
                affected_count += 1
        else:
            # Mark as unselected
            for image in low_quality_images:
                image.is_selected = False
                image.rejection_reason = f"Low quality score: {image.quality_score}"
                affected_count += 1
        
        await db.commit()
        
        # Update dataset image count
        if action == "delete":
            from sqlalchemy import update, func
            count_result = await db.execute(
                select(func.count()).select_from(DatasetImage).where(
                    and_(
                        DatasetImage.dataset_id == dataset_id,
                        DatasetImage.is_selected == True
                    )
                )
            )
            new_count = count_result.scalar()
            
            await db.execute(
                update(TrainingDataset)
                .where(TrainingDataset.id == dataset_id)
                .values(image_count=new_count)
            )
            await db.commit()
        
        return success_response(
            data={
                "affected_count": affected_count,
                "threshold": threshold,
                "action": action
            },
            message=f"{affected_count} images {action}ed with quality < {threshold}"
        )
        
    except Exception as e:
        logger.error(f"Failed to filter low quality images: {e}")
        raise AppException(
            status_code=500,
            error="ServerError",
            message="Failed to filter low quality images"
        )


@router.post("/{dataset_id}/batch-annotate")
async def batch_annotate_images(
    dataset_id: int,
    request: BatchAnnotateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Batch update annotations for multiple images.
    
    Request body:
    {
        "image_ids": [1, 2, 3],  # List of image IDs
        "updates": {
            "angle": "front",
            "expression": "happy",
            "pose": "standing",
            "background": "simple"
        }
    }
    """
    try:
        image_ids = request.image_ids
        updates = request.updates
        
        result = await dataset_manager.batch_update_annotations(
            dataset_id, db, image_ids, updates
        )
        
        return success_response(
            data=result,
            message=f"Updated {result['updated_count']} images successfully"
        )
        
    except (BadRequestException, NotFoundException):
        raise
    except Exception as e:
        logger.error(f"Failed to batch annotate images: {e}")
        raise AppException(
            status_code=500,
            error="ServerError",
            message="Failed to batch annotate images"
        )


# ============================================
# Dataset Generation from Features
# ============================================

@router.post("/generate-from-features")
async def generate_dataset_from_features(
    request: DatasetGenerationRequest,
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
        if not request.selected_features:
            raise BadRequestException("selected_features cannot be empty")
        
        # Generate dataset
        generator = DatasetGenerator(db)
        dataset = await generator.generate_dataset_from_features(
            ip_asset_id=request.ip_asset_id,
            selected_features=request.selected_features,
            dataset_name=request.dataset_name,
            description=request.description,
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
    request: DatasetPreviewRequest,
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
        if not request.selected_features:
            raise BadRequestException("selected_features cannot be empty")
        
        generator = DatasetGenerator(db)
        preview = await generator.preview_combinations(
            ip_asset_id=request.ip_asset_id,
            selected_features=request.selected_features,
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
    request: Optional[DatasetConversionRequest] = None,
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
        output_dir = request.output_dir if request else None
        
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
            raise NotFoundException(resource="Dataset", identifier=str(dataset_id))
        
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


# ============================================
# Data Augmentation
# ============================================

@router.post("/{dataset_id}/augment")
async def apply_data_augmentation(
    dataset_id: int,
    request: DatasetAugmentationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Augment dataset images to increase training data size.
    
    Supports:
    - Horizontal flip
    - Rotation (±15 degrees)
    - Color jitter (brightness, contrast, saturation)
    - Combined augmentations
    
    Request body:
    {
        "augmentation_types": ["flip", "rotation", "color_jitter"],
        "multiplier": 2,
        "create_version": true
    }
    """
    try:
        # Check if dataset exists
        result = await db.execute(
            select(TrainingDataset).where(TrainingDataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        
        if not dataset:
            raise NotFoundException(resource="Dataset", identifier=str(dataset_id))
        
        # Get dataset images
        images_result = await db.execute(
            select(DatasetImage).where(DatasetImage.dataset_id == dataset_id)
        )
        dataset_images = images_result.scalars().all()
        
        if not dataset_images:
            raise BadRequestException("Dataset has no images to augment")
        
        # Prepare image paths
        original_images = [
            {"path": img.file_path, "id": img.id}
            for img in dataset_images
            if img.file_path
        ]
        
        if not original_images:
            raise BadRequestException("No valid image paths found in dataset")
        
        # Perform augmentation
        augmenter = DataAugmentation()
        aug_result = await augmenter.augment_dataset(
            dataset_id=dataset_id,
            original_images=original_images,
            augmentation_types=request.augmentation_types,
            multiplier=request.multiplier,
        )
        
        # Generate report
        report = await augmenter.generate_augmentation_report(
            dataset_id=dataset_id,
            original_count=len(original_images),
            augmented_count=aug_result["augmented_count"],
            augmentation_types=request.augmentation_types,
        )
        
        response_data = {
            "dataset_id": dataset_id,
            "original_count": aug_result["original_count"],
            "augmented_count": aug_result["augmented_count"],
            "output_directory": aug_result["output_directory"],
            "augmentation_types": request.augmentation_types,
            "report": report,
        }
        
        return success_response(
            data=response_data,
            message=f"Dataset augmented: {aug_result['augmented_count']} images created"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Error augmenting dataset: {e}")
        raise BadRequestException(f"Failed to augment dataset: {str(e)}")


@router.post("/{dataset_id}/augment/validate")
async def validate_augmentation_safety(
    dataset_id: int,
    request: AugmentationValidationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Validate if augmentation is safe for dataset images.
    
    Request body:
    {
        "image_id": 123,
        "augmentation_type": "flip"
    }
    """
    try:
        result = await db.execute(
            select(DatasetImage).where(DatasetImage.id == request.image_id)
        )
        dataset_image = result.scalar_one_or_none()
        
        if not dataset_image:
            raise NotFoundException(resource="Dataset image", identifier=str(request.image_id))
        
        if not dataset_image.file_path:
            raise BadRequestException("Image has no file path")
        
        # Validate safety
        augmenter = DataAugmentation()
        safety_result = augmenter.validate_augmentation_safety(
            image_path=dataset_image.file_path,
            aug_type=request.augmentation_type,
        )
        
        return success_response(
            data=safety_result,
            message="Augmentation safety validation completed"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Error validating augmentation safety: {e}")
        raise BadRequestException(f"Failed to validate: {str(e)}")


@router.get("/{dataset_id}/augment/report")
async def get_augmentation_report(
    dataset_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get augmentation report for a dataset.
    """
    try:
        # Check if dataset exists
        result = await db.execute(
            select(TrainingDataset).where(TrainingDataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        
        if not dataset:
            raise NotFoundException(resource="Dataset", identifier=str(dataset_id))
        
        # Get image counts
        images_result = await db.execute(
            select(DatasetImage).where(DatasetImage.dataset_id == dataset_id)
        )
        all_images = images_result.scalars().all()
        
        original_count = sum(1 for img in all_images if not img.file_path or "aug_" not in img.file_path)
        augmented_count = sum(1 for img in all_images if img.file_path and "aug_" in img.file_path)
        
        # Generate report
        augmenter = DataAugmentation()
        report = await augmenter.generate_augmentation_report(
            dataset_id=dataset_id,
            original_count=original_count,
            augmented_count=augmented_count,
            augmentation_types=["flip", "rotation", "color_jitter"],
        )
        
        return success_response(
            data=report,
            message="Augmentation report generated"
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        logger.error(f"Error generating augmentation report: {e}")
        raise BadRequestException(f"Failed to generate report: {str(e)}")

