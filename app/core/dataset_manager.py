"""
Training Dataset Manager Module

Manages training datasets for LoRA model training, including
dataset CRUD operations, image management, and quality validation.
"""
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import os
from datetime import datetime

import cv2
import numpy as np

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.training_dataset import TrainingDataset
from app.models.dataset_image import DatasetImage
from app.models.ip_asset import IPAsset
from app.schemas.training_dataset import (
    TrainingDatasetCreate,
    TrainingDatasetUpdate,
    DatasetImageCreate,
    DatasetValidationReport,
)
from app.core.exceptions import NotFoundException, BadRequestException
from app.core.data_augmentation import data_augmentation
from app.utils.logger import logger

# ============================================================================
# Constants
# ============================================================================

# Quality evaluation weights (can be overridden by settings)
QUALITY_WEIGHTS = settings.DATASET_QUALITY_WEIGHTS if hasattr(settings, 'DATASET_QUALITY_WEIGHTS') else {
    "sharpness": 0.40,
    "contrast": 0.30,
    "brightness": 0.15,
    "resolution": 0.15,
}

# Health score weights
HEALTH_SCORE_WEIGHTS = {
    "quantity": 0.25,
    "quality": 0.35,
    "angle": 0.25,
    "integrity": 0.15,
}

# Health score grade thresholds
HEALTH_SCORE_GRADES = [
    (90, "S"),
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (50, "D"),
]
DEFAULT_HEALTH_GRADE = "F"

# Dataset status thresholds
STATUS_READY_THRESHOLD = 60
STATUS_PENDING_THRESHOLD = 40

# Quantity score thresholds
QUANTITY_THRESHOLDS = [
    (30, 100),
    (20, 80),
    (15, 60),
    (10, 40),
]
QUANTITY_MIN_SCORE_MULTIPLIER = 4

# Required angles for coverage
REQUIRED_ANGLES = ["front", "side", "back"]
MIN_ANGLE_COVERAGE = 3

# Integrity score penalty per issue
INTEGRITY_PENALTY_PER_ISSUE = 20


class DatasetManager:
    """
    Service for managing training datasets.
    
    Handles dataset CRUD operations, image uploads, quality validation,
    and dataset statistics for LoRA training.
    """
    
    def __init__(self):
        """Initialize dataset manager."""
        self.datasets_path = Path(settings.STORAGE_PATH) / "training_datasets"
        self.datasets_path.mkdir(parents=True, exist_ok=True)
        self.augmentation_path = self.datasets_path / "augmented"
        self.augmentation_path.mkdir(parents=True, exist_ok=True)
    
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
                resource="IP asset",
                identifier=str(dataset_data.ip_asset_id)
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
                resource="Training dataset",
                identifier=str(dataset_id)
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
    
    async def evaluate_image_quality(self, image_path: str) -> float:
        """
        Evaluate image quality score (0-100).
        
        Evaluates based on:
        - Sharpness (Laplacian variance) - 40%
        - Contrast (standard deviation) - 30%
        - Brightness (mean pixel value) - 15%
        - Resolution (megapixels) - 15%
        
        Args:
            image_path: Path to image file
            
        Returns:
            Quality score (0-100)
        """
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                logger.warning(f"Failed to read image: {image_path}")
                return 0.0
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 1. Sharpness score (Laplacian variance) - Weight: 40%
            # For cartoon/IP images, lower threshold is acceptable
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            # Adjusted: /3 instead of /5 for more reasonable scoring
            sharpness_score = min(100, laplacian_var / 3)
            
            # 2. Contrast score (standard deviation) - Weight: 30%
            # Higher contrast is better for training
            contrast = np.std(gray)
            # Adjusted: /1.2 instead of /1.5 for better scaling
            contrast_score = min(100, contrast / 1.2)
            
            # 3. Brightness score (mean pixel value) - Weight: 15%
            # Cartoon images can have wider brightness range
            brightness = np.mean(gray)
            # More tolerant: 60-200 range is acceptable
            if 60 <= brightness <= 200:
                brightness_score = 100 - abs(brightness - 130) / 1.5
            else:
                brightness_score = max(0, 50 - abs(brightness - 130) / 3)
            
            # 4. Resolution score (based on megapixels) - Weight: 15%
            # Lower weight since resolution is less critical for training
            height, width = gray.shape
            megapixels = (height * width) / 1_000_000
            # Adjusted: 0.1MP already gets 50 points, 0.2MP+ gets 100
            resolution_score = min(100, megapixels * 500)
            
            # Weighted average
            quality_score = (
                sharpness_score * QUALITY_WEIGHTS["sharpness"] +
                contrast_score * QUALITY_WEIGHTS["contrast"] +
                brightness_score * QUALITY_WEIGHTS["brightness"] +
                resolution_score * QUALITY_WEIGHTS["resolution"]
            )
            
            return round(max(0, min(100, quality_score)), 2)
            
        except Exception as e:
            logger.error(f"Failed to evaluate image quality for {image_path}: {e}")
            return 0.0
    
    async def batch_evaluate_quality(
        self,
        dataset_id: int,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Batch evaluate quality for all images in dataset.
        
        Args:
            dataset_id: Dataset ID
            db: Database session
            
        Returns:
            Evaluation summary
        """
        # Get all images
        result = await db.execute(
            select(DatasetImage).where(DatasetImage.dataset_id == dataset_id)
        )
        images = result.scalars().all()
        
        evaluated = 0
        failed = 0
        total_score = 0.0
        
        for image in images:
            try:
                if Path(image.file_path).exists():
                    quality_score = await self.evaluate_image_quality(image.file_path)
                    image.quality_score = quality_score
                    evaluated += 1
                    total_score += quality_score
                else:
                    logger.warning(f"Image file not found: {image.file_path}")
                    failed += 1
            except Exception as e:
                logger.error(f"Failed to evaluate image {image.id}: {e}")
                failed += 1
        
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit quality scores: {e}")
            raise
        
        avg_score = total_score / evaluated if evaluated > 0 else 0.0
        
        summary = {
            "evaluated": evaluated,
            "failed": failed,
            "total": len(images),
            "average_quality": round(avg_score, 2),
        }
        
        # Auto-update dataset status if quality is good
        if avg_score >= STATUS_READY_THRESHOLD:
            from sqlalchemy import update
            await db.execute(
                update(TrainingDataset)
                .where(TrainingDataset.id == dataset_id)
                .values(status="ready")
            )
            await db.commit()
            logger.info(f"Dataset {dataset_id} status updated to 'ready' after quality evaluation")
        
        logger.info(f"Batch quality evaluation for dataset {dataset_id}: {summary}")
        return summary
    
    async def batch_update_annotations(
        self,
        dataset_id: int,
        db: AsyncSession,
        image_ids: List[int],
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Batch update annotations for multiple images.
        
        Args:
            dataset_id: Dataset ID
            db: Database session
            image_ids: List of image IDs to update
            updates: Dict of fields to update (angle, expression, pose, background)
            
        Returns:
            Update summary
        """
        # Validate batch size
        MAX_BATCH_SIZE = 100
        if len(image_ids) > MAX_BATCH_SIZE:
            raise BadRequestException(
                message=f"Batch size too large: {len(image_ids)} images. Maximum allowed: {MAX_BATCH_SIZE}",
                details={"max_batch_size": MAX_BATCH_SIZE}
            )
        
        if not image_ids:
            raise BadRequestException(
                message="No image IDs provided",
                details={}
            )
        
        # Get images
        result = await db.execute(
            select(DatasetImage).where(
                and_(
                    DatasetImage.id.in_(image_ids),
                    DatasetImage.dataset_id == dataset_id
                )
            )
        )
        images = result.scalars().all()
        
        updated_count = 0
        for image in images:
            if 'angle' in updates:
                image.angle = updates['angle']
            if 'expression' in updates:
                image.expression = updates['expression']
            if 'pose' in updates:
                image.pose = updates['pose']
            if 'background' in updates:
                image.background = updates['background']
            updated_count += 1
        
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit batch annotation updates: {e}")
            raise
        
        summary = {
            "updated_count": updated_count,
            "total_requested": len(image_ids),
        }
        
        logger.info(f"Batch annotation update for dataset {dataset_id}: {summary}")
        return summary
    
    async def get_quality_distribution(
        self,
        dataset_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get quality score distribution for dataset images.
        
        Returns:
            Distribution data for histogram
        """
        # Get all selected images with quality scores
        result = await db.execute(
            select(DatasetImage.quality_score).where(
                and_(
                    DatasetImage.dataset_id == dataset_id,
                    DatasetImage.is_selected == True,
                    DatasetImage.quality_score.isnot(None)
                )
            )
        )
        scores = [row[0] for row in result.all()]
        
        if not scores:
            return {
                "distribution": {},
                "statistics": {
                    "min": 0,
                    "max": 0,
                    "avg": 0,
                    "median": 0,
                    "count": 0
                }
            }
        
        # Calculate distribution (bins of 10 points)
        distribution = {
            "0-10": 0,
            "10-20": 0,
            "20-30": 0,
            "30-40": 0,
            "40-50": 0,
            "50-60": 0,
            "60-70": 0,
            "70-80": 0,
            "80-90": 0,
            "90-100": 0
        }
        
        for score in scores:
            if score < 10:
                distribution["0-10"] += 1
            elif score < 20:
                distribution["10-20"] += 1
            elif score < 30:
                distribution["20-30"] += 1
            elif score < 40:
                distribution["30-40"] += 1
            elif score < 50:
                distribution["40-50"] += 1
            elif score < 60:
                distribution["50-60"] += 1
            elif score < 70:
                distribution["60-70"] += 1
            elif score < 80:
                distribution["70-80"] += 1
            elif score < 90:
                distribution["80-90"] += 1
            else:
                distribution["90-100"] += 1
        
        # Calculate statistics
        statistics = {
            "min": round(float(np.min(scores)), 2),
            "max": round(float(np.max(scores)), 2),
            "avg": round(float(np.mean(scores)), 2),
            "median": round(float(np.median(scores)), 2),
            "count": len(scores)
        }
        
        return {
            "distribution": distribution,
            "statistics": statistics
        }
    
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
        
        # Calculate health score (comprehensive rating)
        health_score = self._calculate_health_score(stats, coverage, issues)
        health_grade = self._get_health_grade(health_score)
        
        report = DatasetValidationReport(
            total_images=stats["total_images"],
            selected_images=stats["selected_images"],
            rejected_images=stats["total_images"] - stats["selected_images"],
            quality_score=round(quality_score, 2),
            angle_coverage=coverage,
            diversity_score=round(len(coverage) * 20, 2),  # Simple diversity metric
            consistency_score=0.0,  # Will be calculated later with CLIP
            health_score=round(health_score, 2),
            health_grade=health_grade,
            issues=issues,
            recommendations=recommendations,
        )
        
        logger.info(f"Dataset validation complete for {dataset_id}: score={quality_score}")
        
        # Auto-update dataset status based on validation result
        await self._update_dataset_status_after_validation(dataset_id, db, report)
        
        return report
    
    async def _update_dataset_status_after_validation(
        self,
        dataset_id: int,
        db: AsyncSession,
        report: DatasetValidationReport
    ) -> None:
        """
        Update dataset status based on validation results.
        
        Rules:
        - quality_score >= 60 and no critical issues -> "ready"
        - quality_score < 60 or has issues -> "pending"
        """
        from sqlalchemy import update
        
        # Determine new status using unified method
        new_status = self._determine_dataset_status(report.quality_score, len(report.issues))
        
        # Update status
        await db.execute(
            update(TrainingDataset)
            .where(TrainingDataset.id == dataset_id)
            .values(
                status=new_status,
                quality_score=report.quality_score,
                validation_report={
                    "quality_score": report.quality_score,
                    "angle_coverage": report.angle_coverage,
                    "diversity_score": report.diversity_score,
                    "issues": report.issues,
                    "recommendations": report.recommendations,
                }
            )
        )
        
        await db.commit()
        logger.info(f"Dataset {dataset_id} status updated to: {new_status}")
    
    def _determine_dataset_status(
        self,
        quality_score: float,
        issue_count: int = 0
    ) -> str:
        """
        Determine dataset status based on quality metrics.
        
        Args:
            quality_score: Quality score (0-100)
            issue_count: Number of issues found
            
        Returns:
            Status string: "ready" or "pending"
        """
        if quality_score >= STATUS_READY_THRESHOLD and issue_count == 0:
            return "ready"
        else:
            return "pending"
    
    def _calculate_health_score(
        self,
        stats: Dict[str, Any],
        coverage: Dict[str, int],
        issues: List[str]
    ) -> float:
        """
        Calculate comprehensive health score (0-100).
        
        Components:
        - Image quantity (25%): Based on total images
        - Image quality (35%): Average quality score
        - Angle coverage (25%): Diversity of angles
        - Data integrity (15%): No critical issues
        """
        # 1. Image quantity score (25%)
        total = stats["total_images"]
        quantity_score = 0
        for threshold, score in QUANTITY_THRESHOLDS:
            if total >= threshold:
                quantity_score = score
                break
        else:
            quantity_score = max(0, total * QUANTITY_MIN_SCORE_MULTIPLIER)
        
        # 2. Image quality score (35%)
        quality_score = stats["avg_quality_score"]
        
        # 3. Angle coverage score (25%)
        covered_angles = sum(1 for angle in REQUIRED_ANGLES if coverage.get(angle, 0) >= MIN_ANGLE_COVERAGE)
        angle_score = (covered_angles / len(REQUIRED_ANGLES)) * 100
        
        # 4. Data integrity score (15%)
        critical_issues = len(issues)
        integrity_score = max(0, 100 - (critical_issues * INTEGRITY_PENALTY_PER_ISSUE))
        
        # Weighted average
        health_score = (
            quantity_score * HEALTH_SCORE_WEIGHTS["quantity"] +
            quality_score * HEALTH_SCORE_WEIGHTS["quality"] +
            angle_score * HEALTH_SCORE_WEIGHTS["angle"] +
            integrity_score * HEALTH_SCORE_WEIGHTS["integrity"]
        )
        
        return round(max(0, min(100, health_score)), 2)
    
    def _get_health_grade(self, health_score: float) -> str:
        """Convert health score to letter grade."""
        for threshold, grade in HEALTH_SCORE_GRADES:
            if health_score >= threshold:
                return grade
        return DEFAULT_HEALTH_GRADE
    
    async def augment_dataset(
        self,
        dataset_id: int,
        db: AsyncSession,
        augmentation_factor: int = 2,
        strategies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Augment dataset images to increase diversity.
        
        Args:
            dataset_id: Dataset ID
            db: Database session
            augmentation_factor: Number of augmented versions per image
            strategies: Specific strategies to apply (default: random)
            
        Returns:
            Augmentation results with statistics
        """
        # Get dataset
        dataset = await self.get_dataset(dataset_id, db)
        
        # Get all selected images
        result = await db.execute(
            select(DatasetImage).where(
                and_(
                    DatasetImage.dataset_id == dataset_id,
                    DatasetImage.is_selected == True,
                    DatasetImage.is_augmented == False  # Only augment original images
                )
            )
        )
        original_images = result.scalars().all()
        
        if not original_images:
            raise BadRequestException(
                message="No original images found to augment",
                details={"dataset_id": dataset_id}
            )
        
        # Prepare image paths
        image_paths = [img.file_path for img in original_images]
        
        # Create augmentation output directory
        aug_dir = self.augmentation_path / f"dataset_{dataset_id}_v{dataset.version}"
        aug_dir.mkdir(parents=True, exist_ok=True)
        
        # Perform augmentation
        logger.info(f"Starting augmentation for dataset {dataset_id}: "
                   f"{len(image_paths)} images x {augmentation_factor} = "
                   f"{len(image_paths) * augmentation_factor} augmented images")
        
        augmentation_results = data_augmentation.augment_dataset(
            image_paths=image_paths,
            output_dir=str(aug_dir),
            augmentation_factor=augmentation_factor,
            strategies=strategies
        )
        
        # Add augmented images to database
        added_count = 0
        for aug_result in augmentation_results:
            # Find parent image
            parent_path = aug_result['input_path']
            parent_image = next(
                (img for img in original_images if img.file_path == parent_path),
                None
            )
            
            if not parent_image:
                continue
            
            # Create augmented image record
            # Inherit 90% of parent's quality score (augmentation may slightly reduce quality)
            inherited_quality = parent_image.quality_score * 0.9 if parent_image.quality_score else None
            
            augmented_image = DatasetImage(
                dataset_id=dataset_id,
                file_path=aug_result['output_path'],
                width=aug_result['output_size'][0],
                height=aug_result['output_size'][1],
                file_size_kb=aug_result['file_size_kb'],
                angle=parent_image.angle,
                expression=parent_image.expression,
                pose=parent_image.pose,
                background=parent_image.background,
                quality_score=round(inherited_quality, 2) if inherited_quality else None,
                is_augmented=True,
                parent_image_id=parent_image.id,
            )
            
            db.add(augmented_image)
            added_count += 1
        
        # Update dataset statistics
        dataset.augmented_count = added_count
        
        # Reset status to pending since dataset needs re-validation after augmentation
        dataset.status = "pending"
        
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit augmentation results: {e}")
            raise
        
        # Generate augmentation report
        report = data_augmentation.get_augmentation_report(augmentation_results)
        report['added_to_database'] = added_count
        
        logger.info(f"Augmentation complete for dataset {dataset_id}: "
                   f"{added_count} images added")
        
        return report
    
    async def create_dataset_version(
        self,
        dataset_id: int,
        db: AsyncSession,
        version_note: Optional[str] = None
    ) -> TrainingDataset:
        """
        Create a new version of the dataset.
        
        Args:
            dataset_id: Dataset ID
            db: Database session
            version_note: Note about this version
            
        Returns:
            New version dataset
        """
        # Get current dataset
        current_dataset = await self.get_dataset(dataset_id, db)
        
        # Create new version
        new_version = TrainingDataset(
            ip_asset_id=current_dataset.ip_asset_id,
            name=f"{current_dataset.name} v{current_dataset.version + 1}",
            description=current_dataset.description,
            status="pending",
            version=current_dataset.version + 1,
            parent_version_id=current_dataset.id,
        )
        
        db.add(new_version)
        await db.commit()
        await db.refresh(new_version)
        
        logger.info(f"Created dataset version {new_version.version} for dataset {dataset_id}")
        return new_version


# Singleton instance
dataset_manager = DatasetManager()
