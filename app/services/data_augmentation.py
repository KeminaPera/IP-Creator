"""
Data Augmentation Service

Provides image augmentation capabilities for training datasets
to improve LoRA model quality and prevent overfitting.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import random
from app.utils.time_utils import get_timestamp_filename
from PIL import Image, ImageEnhance, ImageFilter
from app.utils.logger import logger
from app.config.settings import settings


class DataAugmentation:
    """
    Service for augmenting training datasets.
    
    Supports:
    - Horizontal flip
    - Rotation (±15 degrees)
    - Color jitter (brightness, contrast, saturation)
    - Combined augmentations
    """
    
    def __init__(self):
        """Initialize data augmentation service."""
        self.augmented_dir = Path(settings.STORAGE_PATH) / "augmented_datasets"
        self.augmented_dir.mkdir(parents=True, exist_ok=True)
    
    async def augment_dataset(
        self,
        dataset_id: int,
        original_images: List[Dict[str, Any]],
        augmentation_types: List[str] = None,
        multiplier: int = 2,
    ) -> Dict[str, Any]:
        """
        Augment dataset images to increase training data size.
        
        Args:
            dataset_id: Original dataset ID
            original_images: List of image info dicts with 'path' key
            augmentation_types: Types of augmentation to apply
                Options: ['flip', 'rotation', 'color_jitter', 'combined']
            multiplier: How many augmented versions per image (default: 2)
            
        Returns:
            Dict with augmentation results and new image paths
        """
        if augmentation_types is None:
            augmentation_types = ['flip', 'rotation', 'color_jitter']
        
        logger.info(
            f"Augmenting dataset {dataset_id}: "
            f"{len(original_images)} images × {multiplier} = "
            f"{len(original_images) * multiplier} new images"
        )
        
        # Create output directory
        timestamp = get_timestamp_filename()
        output_dir = self.augmented_dir / f"dataset_{dataset_id}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        augmented_images = []
        total_created = 0
        
        for img_info in original_images:
            original_path = img_info.get('path')
            if not original_path or not Path(original_path).exists():
                logger.warning(f"Image not found: {original_path}")
                continue
            
            try:
                # Open original image
                original_img = Image.open(original_path).convert('RGB')
                
                # Generate augmented versions
                for i in range(multiplier):
                    aug_type = augmentation_types[i % len(augmentation_types)]
                    augmented_img = self._apply_augmentation(original_img, aug_type)
                    
                    # Save augmented image
                    aug_filename = f"aug_{total_created:04d}_{aug_type}.jpg"
                    aug_path = output_dir / aug_filename
                    augmented_img.save(str(aug_path), quality=95)
                    
                    augmented_images.append({
                        "original_path": original_path,
                        "augmented_path": str(aug_path),
                        "augmentation_type": aug_type,
                        "index": total_created,
                    })
                    
                    total_created += 1
            
            except Exception as e:
                logger.error(f"Failed to augment image {original_path}: {e}")
                continue
        
        result = {
            "dataset_id": dataset_id,
            "output_directory": str(output_dir),
            "original_count": len(original_images),
            "augmented_count": len(augmented_images),
            "multiplier": multiplier,
            "augmentation_types": augmentation_types,
            "augmented_images": augmented_images,
        }
        
        logger.info(f"Dataset augmentation complete: {len(augmented_images)} images created")
        return result
    
    def _apply_augmentation(
        self,
        image: Image.Image,
        aug_type: str,
    ) -> Image.Image:
        """
        Apply specific augmentation to an image.
        
        Args:
            image: PIL Image object
            aug_type: Type of augmentation
            
        Returns:
            Augmented PIL Image
        """
        if aug_type == 'flip':
            return self._horizontal_flip(image)
        elif aug_type == 'rotation':
            return self._random_rotation(image)
        elif aug_type == 'color_jitter':
            return self._color_jitter(image)
        elif aug_type == 'combined':
            return self._combined_augmentation(image)
        else:
            logger.warning(f"Unknown augmentation type: {aug_type}")
            return image
    
    def _horizontal_flip(self, image: Image.Image) -> Image.Image:
        """Apply horizontal flip."""
        return image.transpose(Image.FLIP_LEFT_RIGHT)
    
    def _random_rotation(self, image: Image.Image) -> Image.Image:
        """Apply random rotation within ±15 degrees."""
        angle = random.uniform(-15, 15)
        return image.rotate(angle, resample=Image.BICUBIC, expand=False)
    
    def _color_jitter(self, image: Image.Image) -> Image.Image:
        """Apply random color adjustments."""
        # Random brightness (0.8 to 1.2)
        brightness_factor = random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(brightness_factor)
        
        # Random contrast (0.8 to 1.2)
        contrast_factor = random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(contrast_factor)
        
        # Random saturation (0.8 to 1.2)
        saturation_factor = random.uniform(0.8, 1.2)
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(saturation_factor)
        
        return image
    
    def _combined_augmentation(self, image: Image.Image) -> Image.Image:
        """Apply combined augmentations (flip + rotation + color)."""
        # 50% chance of flip
        if random.random() > 0.5:
            image = self._horizontal_flip(image)
        
        # Random rotation
        image = self._random_rotation(image)
        
        # Color jitter
        image = self._color_jitter(image)
        
        return image
    
    async def create_augmented_version(
        self,
        dataset_id: int,
        version_name: str,
        original_images: List[Dict[str, Any]],
        augmentation_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new augmented version of a dataset.
        
        Args:
            dataset_id: Original dataset ID
            version_name: Name for the augmented version
            original_images: List of original image paths
            augmentation_config: Configuration for augmentation
                Example: {
                    "types": ["flip", "rotation"],
                    "multiplier": 2,
                    "randomize": true
                }
                
        Returns:
            Augmentation result with metadata
        """
        logger.info(f"Creating augmented version '{version_name}' for dataset {dataset_id}")
        
        # Extract config
        aug_types = augmentation_config.get('types', ['flip', 'rotation', 'color_jitter'])
        multiplier = augmentation_config.get('multiplier', 2)
        randomize = augmentation_config.get('randomize', True)
        
        # Shuffle if randomize enabled
        if randomize:
            random.shuffle(aug_types)
        
        # Perform augmentation
        result = await self.augment_dataset(
            dataset_id=dataset_id,
            original_images=original_images,
            augmentation_types=aug_types,
            multiplier=multiplier,
        )
        
        # Add version metadata
        result['version_name'] = version_name
        result['created_at'] = datetime.now().isoformat()
        result['config'] = augmentation_config
        
        return result
    
    def validate_augmentation_safety(
        self,
        image_path: str,
        aug_type: str,
    ) -> Dict[str, Any]:
        """
        Validate if augmentation is safe for a specific image.
        
        Some augmentations may not be suitable for certain images
        (e.g., flipping images with text).
        
        Args:
            image_path: Path to the image
            aug_type: Type of augmentation to validate
            
        Returns:
            Validation result with safety score and warnings
        """
        result = {
            "safe": True,
            "warnings": [],
            "safety_score": 1.0,
        }
        
        try:
            img = Image.open(image_path)
            width, height = img.size
            
            # Check for very small images
            if width < 256 or height < 256:
                result["warnings"].append(
                    f"Image is small ({width}x{height}). Augmentation may reduce quality."
                )
                result["safety_score"] = 0.7
            
            # Check for asymmetric images (flipping may be problematic)
            if aug_type == 'flip' and abs(width - height) / max(width, height) > 0.5:
                result["warnings"].append(
                    "Image is very asymmetric. Horizontal flip may look unnatural."
                )
                result["safety_score"] *= 0.8
            
            # Rotation is generally safe
            if aug_type == 'rotation':
                result["safety_score"] = min(result["safety_score"], 0.95)
            
            # Color jitter is very safe
            if aug_type == 'color_jitter':
                result["safety_score"] = min(result["safety_score"], 0.98)
            
        except Exception as e:
            result["safe"] = False
            result["warnings"].append(f"Failed to validate image: {str(e)}")
            result["safety_score"] = 0.0
        
        return result
    
    async def generate_augmentation_report(
        self,
        dataset_id: int,
        original_count: int,
        augmented_count: int,
        augmentation_types: List[str],
    ) -> Dict[str, Any]:
        """
        Generate a report about dataset augmentation.
        
        Args:
            dataset_id: Dataset ID
            original_count: Number of original images
            augmented_count: Number of augmented images
            augmentation_types: Types of augmentation used
            
        Returns:
            Augmentation report
        """
        augmentation_factor = augmented_count / original_count if original_count > 0 else 0
        
        report = {
            "dataset_id": dataset_id,
            "original_count": original_count,
            "augmented_count": augmented_count,
            "total_images": original_count + augmented_count,
            "augmentation_factor": round(augmentation_factor, 2),
            "augmentation_types": augmentation_types,
            "recommendations": [],
        }
        
        # Generate recommendations
        if augmentation_factor < 1.5:
            report["recommendations"].append(
                "Low augmentation factor. Consider using multiplier of 2-3 for better results."
            )
        elif augmentation_factor > 5:
            report["recommendations"].append(
                "High augmentation factor. Monitor training for signs of overfitting to augmented data."
            )
        
        if 'flip' in augmentation_types and 'rotation' not in augmentation_types:
            report["recommendations"].append(
                "Consider adding rotation augmentation for better angle coverage."
            )
        
        if original_count < 10:
            report["recommendations"].append(
                "Very small dataset. Augmentation is critical - consider using multiplier of 3-4."
            )
        elif original_count >= 30:
            report["recommendations"].append(
                "Large dataset. Augmentation may not be necessary unless specific angles are missing."
            )
        
        return report
