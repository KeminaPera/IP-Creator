"""
Data Augmentation Service

Provides image augmentation capabilities for training datasets,
including flip, rotation, color jitter, and brightness adjustment.
"""
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
import cv2

from app.utils.logger import logger


class DataAugmentation:
    """
    Service for augmenting training dataset images.
    
    Provides various augmentation strategies to increase dataset
    diversity and improve LoRA training quality.
    """
    
    def __init__(self):
        """Initialize data augmentation service."""
        self.augmentation_strategies = {
            'horizontal_flip': self.horizontal_flip,
            'rotation': self.rotation,
            'brightness': self.brightness_adjustment,
            'contrast': self.contrast_adjustment,
            'color_jitter': self.color_jitter,
        }
    
    def horizontal_flip(
        self,
        image: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Horizontal flip (mirror) augmentation.
        
        Args:
            image: Input image (numpy array)
            **kwargs: Additional parameters (unused)
            
        Returns:
            Flipped image
        """
        return cv2.flip(image, 1)
    
    def rotation(
        self,
        image: np.ndarray,
        angle: float = 15.0,
        **kwargs
    ) -> np.ndarray:
        """
        Rotation augmentation.
        
        Args:
            image: Input image
            angle: Maximum rotation angle in degrees (default: ±15)
            **kwargs: Additional parameters (unused)
            
        Returns:
            Rotated image
        """
        # Random angle within range
        actual_angle = np.random.uniform(-angle, angle)
        
        # Get image dimensions
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        # Get rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, actual_angle, 1.0)
        
        # Calculate new bounding box dimensions
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        # Adjust rotation matrix to account for translation
        rotation_matrix[0, 2] += (new_w / 2) - center[0]
        rotation_matrix[1, 2] += (new_h / 2) - center[1]
        
        # Perform rotation
        rotated = cv2.warpAffine(image, rotation_matrix, (new_w, new_h))
        
        return rotated
    
    def brightness_adjustment(
        self,
        image: np.ndarray,
        factor: Optional[float] = None,
        **kwargs
    ) -> np.ndarray:
        """
        Brightness adjustment augmentation.
        
        Args:
            image: Input image
            factor: Brightness factor (0.5-1.5, default: random)
            **kwargs: Additional parameters (unused)
            
        Returns:
            Brightness-adjusted image
        """
        if factor is None:
            factor = np.random.uniform(0.7, 1.3)
        
        # Convert to float32 for calculation
        adjusted = image.astype(np.float32) * factor
        
        # Clip values and convert back to uint8
        adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
        
        return adjusted
    
    def contrast_adjustment(
        self,
        image: np.ndarray,
        factor: Optional[float] = None,
        **kwargs
    ) -> np.ndarray:
        """
        Contrast adjustment augmentation.
        
        Args:
            image: Input image
            factor: Contrast factor (0.5-1.5, default: random)
            **kwargs: Additional parameters (unused)
            
        Returns:
            Contrast-adjusted image
        """
        if factor is None:
            factor = np.random.uniform(0.8, 1.2)
        
        # Convert to float32 for calculation
        adjusted = image.astype(np.float32) * factor
        
        # Add mean offset to preserve brightness
        mean = np.mean(image)
        adjusted = adjusted - mean * (factor - 1)
        
        # Clip values and convert back to uint8
        adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
        
        return adjusted
    
    def color_jitter(
        self,
        image: np.ndarray,
        hue_shift: float = 10.0,
        sat_scale: float = 0.2,
        **kwargs
    ) -> np.ndarray:
        """
        Color jittering augmentation (HSV space).
        
        Args:
            image: Input image
            hue_shift: Maximum hue shift (default: ±10)
            sat_scale: Saturation scale factor (default: ±20%)
            **kwargs: Additional parameters (unused)
            
        Returns:
            Color-jittered image
        """
        # Convert to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        
        # Apply random hue shift
        h, s, v = cv2.split(hsv)
        h = (h + np.random.uniform(-hue_shift, hue_shift)) % 180
        
        # Apply random saturation scale
        s = np.clip(s * np.random.uniform(1 - sat_scale, 1 + sat_scale), 0, 255)
        
        # Merge channels
        hsv_jittered = cv2.merge([h, s, v]).astype(np.uint8)
        
        # Convert back to BGR
        jittered = cv2.cvtColor(hsv_jittered, cv2.COLOR_HSV2BGR)
        
        return jittered
    
    def augment_image(
        self,
        image_path: str,
        output_path: str,
        strategies: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Apply augmentation strategies to an image.
        
        Args:
            image_path: Path to input image
            output_path: Path to save augmented image
            strategies: List of augmentation strategies to apply
                       (default: random selection of 1-2 strategies)
            **kwargs: Additional parameters for specific strategies
            
        Returns:
            Dictionary with augmentation results
        """
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        original_h, original_w = image.shape[:2]
        
        # If no strategies specified, randomly select 1-2
        if strategies is None:
            num_strategies = np.random.randint(1, 3)
            strategies = list(np.random.choice(
                list(self.augmentation_strategies.keys()),
                size=num_strategies,
                replace=False
            ))
        
        # Apply strategies sequentially
        augmented = image.copy()
        applied_strategies = []
        
        for strategy in strategies:
            if strategy in self.augmentation_strategies:
                augmented = self.augmentation_strategies[strategy](
                    augmented, **kwargs
                )
                applied_strategies.append(strategy)
            else:
                logger.warning(f"Unknown augmentation strategy: {strategy}")
        
        # Save augmented image
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        success = cv2.imwrite(output_path, augmented)
        
        if not success:
            raise RuntimeError(f"Failed to save augmented image: {output_path}")
        
        # Get output image info
        output_h, output_w = augmented.shape[:2]
        file_size_kb = Path(output_path).stat().st_size // 1024
        
        result = {
            'input_path': image_path,
            'output_path': output_path,
            'applied_strategies': applied_strategies,
            'original_size': (original_w, original_h),
            'output_size': (output_w, output_h),
            'file_size_kb': file_size_kb,
        }
        
        logger.info(f"Augmented image: {image_path} -> {output_path} "
                   f"(strategies: {', '.join(applied_strategies)})")
        
        return result
    
    def augment_dataset(
        self,
        image_paths: List[str],
        output_dir: str,
        augmentation_factor: int = 2,
        strategies: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Augment a dataset of images.
        
        Args:
            image_paths: List of input image paths
            output_dir: Directory to save augmented images
            augmentation_factor: Number of augmented versions per image
            strategies: Specific strategies to apply (default: random)
            
        Returns:
            List of augmentation results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        all_results = []
        
        for image_path in image_paths:
            image_path_obj = Path(image_path)
            
            if not image_path_obj.exists():
                logger.warning(f"Image not found, skipping: {image_path}")
                continue
            
            # Generate augmented versions
            for i in range(augmentation_factor):
                # Create output filename
                stem = image_path_obj.stem
                suffix = image_path_obj.suffix
                output_filename = f"{stem}_aug_{i+1}{suffix}"
                output_file = output_path / output_filename
                
                try:
                    result = self.augment_image(
                        str(image_path_obj),
                        str(output_file),
                        strategies=strategies
                    )
                    all_results.append(result)
                except Exception as e:
                    logger.error(f"Failed to augment {image_path}: {e}")
                    continue
        
        logger.info(f"Dataset augmentation complete: "
                   f"{len(all_results)} images generated")
        
        return all_results
    
    def get_augmentation_report(
        self,
        augmentation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a report on augmentation results.
        
        Args:
            augmentation_results: List of augmentation result dictionaries
            
        Returns:
            Report dictionary with statistics
        """
        if not augmentation_results:
            return {'total': 0}
        
        # Count strategy usage
        strategy_counts = {}
        total_size_kb = 0
        
        for result in augmentation_results:
            for strategy in result.get('applied_strategies', []):
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            total_size_kb += result.get('file_size_kb', 0)
        
        report = {
            'total_augmented': len(augmentation_results),
            'strategy_usage': strategy_counts,
            'total_size_kb': total_size_kb,
            'avg_file_size_kb': round(total_size_kb / len(augmentation_results), 2),
        }
        
        return report


# Singleton instance
data_augmentation = DataAugmentation()
