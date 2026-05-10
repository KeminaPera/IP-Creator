"""
Training Dataset Manager Module

Manages training datasets for LoRA model training, including
dataset CRUD operations, image management, and quality validation.
"""
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import os
from datetime import datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training_dataset import TrainingDataset
from app.models.dataset_image import DatasetImage
from app.models.ip_asset import IPAsset
from app.schemas.training_dataset import (
    TrainingDatasetCreate,
    TrainingDatasetUpdate,
    DatasetImageCreate,
    DatasetValidationReport,
)
from app.config.settings import settings
from app.utils.logger import logger
from app.config.database import async_session_factory
from app.core.exceptions import NotFoundException, BadRequestException


class DatasetManager:
    """
    Service for managing training datasets.
    
    Handles dataset CRUD operations, image uploads, quality validation,
    and dataset statistics for LoRA training.
    """
    
    def __init__(self):
        """Initialize dataset manager."""
        self.datasets_path = Path(settings.DATA_PATH) / "training_datasets"
        self.datasets_path.mkdir(parents=True, exist_ok=True)
    
    async def create_dataset(
        self,
        dataset_data: TrainingDatasetCreate,
        db: AsyncSession
    ) -> TrainingDataset:
        """
        Create a new training dataset.
        
        Args:
            dataset_data: Dataset creation data
            db: Database session
            
        Returns:
            Created training dataset
        """
        # Verify IP asset exists
        result = await db.execute(
            select(IPAsset).where(IPAsset.id == dataset_data.ip_asset_id)
        )
        ip_asset = result.scalar_one_or_none()
        
        if not ip_asset:
            raise NotFoundException(
                message=f"IP asset {dataset_data.ip_asset_id} not found",
                details={"ip_asset_id": dataset_data.ip_asset_id}
            )
        
        # Create dataset directory
        dataset_dir = self.datasets_path / f"dataset_{dataset_data.ip_asset_id}"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dataset record
        dataset = TrainingDataset(
            ip_asset_id=dataset_data.ip_asset_id,
            name=dataset_data.name,
            description=dataset_data.description,
            status="pending",
            version=1,
        )
        
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)
        
        logger.info(f"Created training dataset: {dataset.name} for IP {ip_asset.name}")
        return dataset
    
    async def get_dataset(
        self,
        dataset_id: int,
        db: AsyncSession,
        include_images: bool = False
    ) -> TrainingDataset:
        """
        Get dataset by ID.
        
        Args:
            dataset_id: Dataset ID
            db: Database session
            include_images: Whether to include images
            
        Returns:
            Training dataset or None
        """
        query = select(TrainingDataset).where(TrainingDataset.id == dataset_id)
        
        if include_images:
            from sqlalchemy.orm import selectinload
            query = query.options(selectinload(TrainingDataset.images))
        
        result = await db.execute(query)
        dataset = result.scalar_one_or_none()
        
        if not dataset:
            raise NotFoundException(
                message=f"Training dataset {dataset_id} not found",
                details={"dataset_id": dataset_id}
            )
        
        return dataset
    
    async def list_datasets(
        self,
        db: AsyncSession,
        ip_asset_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[TrainingDataset], int]:
        """
        List training datasets with filtering and pagination.
        
        Args:
            db: Database session
            ip_asset_id: Filter by IP asset ID
            status: Filter by status
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (datasets, total_count)
        """
        query = select(TrainingDataset)
        count_query = select(func.count()).select_from(TrainingDataset)
        
        # Apply filters
        if ip_asset_id:
            query = query.where(TrainingDataset.ip_asset_id == ip_asset_id)
            count_query = count_query.where(TrainingDataset.ip_asset_id == ip_asset_id)
        
        if status:
            query = query.where(TrainingDataset.status == status)
            count_query = count_query.where(TrainingDataset.status == status)
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.offset(skip).limit(limit).order_by(TrainingDataset.created_at.desc())
        
        result = await db.execute(query)
        datasets = result.scalars().all()
        
        return datasets, total
    
    async def update_dataset(
        self,
        dataset_id: int,
        dataset_data: TrainingDatasetUpdate,
        db: AsyncSession
    ) -> TrainingDataset:
        """
        Update dataset.
        
        Args:
            dataset_id: Dataset ID
            dataset_data: Update data
            db: Database session
            
        Returns:
            Updated dataset
        """
        dataset = await self.get_dataset(dataset_id, db)
        
        # Update fields
        update_data = dataset_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(dataset, field, value)
        
        await db.commit()
        await db.refresh(dataset)
        
        logger.info(f"Updated dataset: {dataset.name}")
        return dataset
    
    async def delete_dataset(
        self,
        dataset_id: int,
        db: AsyncSession
    ) -> bool:
        """
        Delete dataset and all associated images.
        
        Args:
            dataset_id: Dataset ID
            db: Database session
            
        Returns:
            True if deleted
        """
        dataset = await self.get_dataset(dataset_id, db, include_images=True)
        
        # Delete image files
        for image in dataset.images:
            image_path = Path(image.file_path)
            if image_path.exists():
                try:
                    image_path.unlink()
                    logger.debug(f"Deleted image file: {image_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete image file {image_path}: {e}")
        
        # Delete dataset directory if empty
        dataset_dir = self.datasets_path / f"dataset_{dataset.ip_asset_id}"
        if dataset_dir.exists() and not any(dataset_dir.iterdir()):
            dataset_dir.rmdir()
        
        # Delete from database
        await db.delete(dataset)
        await db.commit()
        
        logger.info(f"Deleted dataset: {dataset.name}")
        return True
    
    async def add_image(
        self,
        dataset_id: int,
        image_data: DatasetImageCreate,
        db: AsyncSession
    ) -> DatasetImage:
        """
        Add an image to dataset.
        
        Args:
            dataset_id: Dataset ID
            image_data: Image creation data
            db: Database session
            
        Returns:
            Created dataset image
        """
        dataset = await self.get_dataset(dataset_id, db)
        
        # Verify file exists
        file_path = Path(image_data.file_path)
        if not file_path.exists():
            raise BadRequestException(
                message=f"Image file not found: {image_data.file_path}",
                details={"file_path": image_data.file_path}
            )
        
        # Get file metadata
        file_size_kb = file_path.stat().st_size // 1024
        
        # Create image record
        image = DatasetImage(
            dataset_id=dataset_id,
            file_path=str(file_path),
            width=image_data.width,
            height=image_data.height,
            file_size_kb=file_size_kb,
            angle=image_data.angle,
            expression=image_data.expression,
            pose=image_data.pose,
            background=image_data.background,
            quality_score=image_data.quality_score,
            is_augmented=image_data.is_augmented,
            parent_image_id=image_data.parent_image_id,
        )
        
        db.add(image)
        
        # Update dataset statistics
        dataset.image_count += 1
        if image.is_augmented:
            dataset.augmented_count += 1
        
        await db.commit()
        await db.refresh(image)
        
        logger.info(f"Added image to dataset {dataset_id}: {image.file_path}")
        return image
    
    async def calculate_dataset_stats(
        self,
        dataset_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Calculate dataset statistics.
        
        Args:
            dataset_id: Dataset ID
            db: Database session
            
        Returns:
            Statistics dictionary
        """
        dataset = await self.get_dataset(dataset_id, db)
        
        # Get image count
        count_query = select(func.count()).select_from(DatasetImage).where(
            DatasetImage.dataset_id == dataset_id
        )
        count_result = await db.execute(count_query)
        total_images = count_result.scalar()
        
        # Get selected image count
        selected_query = select(func.count()).select_from(DatasetImage).where(
            and_(
                DatasetImage.dataset_id == dataset_id,
                DatasetImage.is_selected == True
            )
        )
        selected_result = await db.execute(selected_query)
        selected_images = selected_result.scalar()
        
        # Calculate average quality
        quality_query = select(func.avg(DatasetImage.quality_score)).where(
            and_(
                DatasetImage.dataset_id == dataset_id,
                DatasetImage.quality_score.isnot(None)
            )
        )
        quality_result = await db.execute(quality_query)
        avg_quality = quality_result.scalar() or 0.0
        
        # Get angle distribution
        angle_query = select(
            DatasetImage.angle,
            func.count(DatasetImage.id)
        ).where(
            and_(
                DatasetImage.dataset_id == dataset_id,
                DatasetImage.is_selected == True
            )
        ).group_by(DatasetImage.angle)
        
        angle_result = await db.execute(angle_query)
        angle_coverage = {angle: count for angle, count in angle_result.all() if angle}
        
        stats = {
            "total_images": total_images,
            "selected_images": selected_images,
            "avg_quality_score": round(avg_quality, 2),
            "angle_coverage": angle_coverage,
        }
        
        logger.info(f"Calculated stats for dataset {dataset_id}: {stats}")
        return stats
    
    async def validate_dataset(
        self,
        dataset_id: int,
        db: AsyncSession,
        min_images: int = 10,
        min_quality: float = 50.0
    ) -> DatasetValidationReport:
        """
        Validate dataset quality and readiness for training.
        
        Args:
            dataset_id: Dataset ID
            db: Database session
            min_images: Minimum required images
            min_quality: Minimum average quality score
            
        Returns:
            Validation report
        """
        stats = await self.calculate_dataset_stats(dataset_id, db)
        
        issues = []
        recommendations = []
        
        # Check minimum images
        if stats["total_images"] < min_images:
            issues.append(f"Insufficient images: {stats['total_images']} < {min_images}")
            recommendations.append(f"Add at least {min_images - stats['total_images']} more images")
        
        # Check quality
        if stats["avg_quality_score"] < min_quality:
            issues.append(f"Low average quality: {stats['avg_quality_score']} < {min_quality}")
            recommendations.append("Improve image quality or replace low-quality images")
        
        # Check angle coverage
        required_angles = ["front", "side", "back"]
        coverage = stats["angle_coverage"]
        missing_angles = [angle for angle in required_angles if angle not in coverage or coverage[angle] < 3]
        
        if missing_angles:
            issues.append(f"Missing angle coverage: {', '.join(missing_angles)}")
            recommendations.append(f"Add more images from angles: {', '.join(missing_angles)}")
        
        # Calculate overall quality score
        quality_score = stats["avg_quality_score"]
        
        # Adjust for angle coverage (bonus for good coverage)
        angle_bonus = min(10, len(coverage) * 2)
        quality_score = min(100, quality_score + angle_bonus)
        
        # Penalties
        if len(issues) > 0:
            quality_score -= len(issues) * 5
        
        quality_score = max(0, quality_score)
        
        report = DatasetValidationReport(
            total_images=stats["total_images"],
            selected_images=stats["selected_images"],
            rejected_images=stats["total_images"] - stats["selected_images"],
            quality_score=round(quality_score, 2),
            angle_coverage=coverage,
            diversity_score=round(len(coverage) * 20, 2),  # Simple diversity metric
            consistency_score=0.0,  # Will be calculated later with CLIP
            issues=issues,
            recommendations=recommendations,
        )
        
        logger.info(f"Dataset validation complete for {dataset_id}: score={quality_score}")
        return report


# Singleton instance
dataset_manager = DatasetManager()
