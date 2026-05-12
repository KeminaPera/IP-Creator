"""
Dataset Generator Service

Generates training datasets from IP feature library by combining
different features (outfits, expressions, poses) with multiple angles.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ip_feature_library import IPFeatureLibrary
from app.models.ip_feature_image import IPFeatureImage
from app.models.training_dataset import TrainingDataset
from app.models.dataset_image import DatasetImage
from app.models.ip_asset import IPAsset
from app.utils.logger import logger
import os
import json
from pathlib import Path


class DatasetGenerator:
    """
    Service for generating training datasets from IP features.
    
    Combines different features (outfits, expressions, poses) 
    with multiple angles to create comprehensive training datasets.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_dataset_from_features(
        self,
        ip_asset_id: int,
        selected_features: Dict[str, List[int]],
        dataset_name: str,
        description: str = "",
    ) -> TrainingDataset:
        """
        Generate training dataset by combining selected features.
        
        Args:
            ip_asset_id: IP asset ID
            selected_features: Dict of feature_type -> list of feature_ids
                Example: {
                    "outfit": [1, 2],  # 常服, 和服
                    "expression": [3, 4, 5],  # 中性, 开心, 生气
                    "pose": [6, 7]  # 站立, 坐着
                }
            dataset_name: Name for the new dataset
            description: Dataset description
            
        Returns:
            Created TrainingDataset instance
        """
        logger.info(f"Generating dataset for IP {ip_asset_id}: {dataset_name}")
        logger.info(f"Selected features: {selected_features}")
        
        # 1. Get IP asset
        ip_asset = await self.db.get(IPAsset, ip_asset_id)
        if not ip_asset:
            raise ValueError(f"IP asset {ip_asset_id} not found")
        
        # 2. Load selected features with their images
        feature_data = {}
        for feature_type, feature_ids in selected_features.items():
            features = await self._load_features(feature_ids, feature_type)
            feature_data[feature_type] = features
        
        # 3. Calculate combinations
        combinations = self._calculate_combinations(feature_data)
        total_images = len(combinations)
        
        logger.info(f"Total combinations: {total_images}")
        
        # 4. Create dataset record
        dataset = TrainingDataset(
            ip_asset_id=ip_asset_id,
            name=dataset_name,
            description=description,
            image_count=total_images,
            augmented_count=0,
            status="pending",
        )
        
        self.db.add(dataset)
        await self.db.flush()  # Get dataset ID
        
        # 5. Generate dataset images
        dataset_images = []
        for i, combination in enumerate(combinations):
            # Generate caption
            caption = self._generate_caption(ip_asset, combination)
            
            # Generate image path (placeholder - will be created during conversion)
            image_path = f"datasets/{dataset.id}/image_{i+1:04d}.jpg"
            
            # Create dataset image record
            dataset_image = DatasetImage(
                dataset_id=dataset.id,
                file_path=image_path,
                caption=caption,
                angle=combination.get("angle", "front"),
                expression=combination.get("expression", "neutral"),
                pose=combination.get("pose", "standing"),
                outfit=combination.get("outfit", "default"),
            )
            
            dataset_images.append(dataset_image)
        
        self.db.add_all(dataset_images)
        await self.db.flush()
        
        # 6. Update dataset statistics
        dataset.status = "ready"
        dataset.validation_report = {
            "total_combinations": total_images,
            "feature_breakdown": {
                ftype: len(feats) for ftype, feats in feature_data.items()
            },
            "caption_format": "dynamic",
        }
        
        await self.db.commit()
        await self.db.refresh(dataset)
        
        logger.info(f"Dataset created successfully: {dataset.id} with {total_images} images")
        
        return dataset
    
    async def _load_features(
        self, 
        feature_ids: List[int], 
        feature_type: str
    ) -> List[Dict[str, Any]]:
        """Load features with their images."""
        
        query = (
            select(IPFeatureLibrary)
            .where(
                IPFeatureLibrary.id.in_(feature_ids),
                IPFeatureLibrary.feature_type == feature_type,
                IPFeatureLibrary.is_active == True
            )
        )
        
        result = await self.db.execute(query)
        features = result.scalars().all()
        
        feature_data = []
        for feature in features:
            # Load feature images
            images_query = select(IPFeatureImage).where(
                IPFeatureImage.feature_id == feature.id
            )
            images_result = await self.db.execute(images_query)
            images = images_result.scalars().all()
            
            feature_data.append({
                "id": feature.id,
                "name": feature.feature_name,
                "type": feature.feature_type,
                "trigger_phrase": feature.trigger_phrase,
                "images": [
                    {
                        "angle": img.angle,
                        "path": img.image_path,
                    }
                    for img in images
                ]
            })
        
        return feature_data
    
    def _calculate_combinations(
        self, 
        feature_data: Dict[str, List[Dict]]
    ) -> List[Dict[str, str]]:
        """
        Calculate all possible combinations of features.
        
        Returns list of combinations, each with feature assignments.
        """
        import itertools
        
        # Extract feature lists
        feature_lists = {}
        for ftype, features in feature_data.items():
            feature_lists[ftype] = features
        
        # Get all types
        types = list(feature_lists.keys())
        
        if not types:
            return []
        
        # Create combinations
        combinations = []
        
        # Get values for each type
        values_by_type = {ftype: feature_lists[ftype] for ftype in types}
        
        # Generate cartesian product
        keys = list(values_by_type.keys())
        value_lists = [values_by_type[k] for k in keys]
        
        for combo in itertools.product(*value_lists):
            combination = {}
            
            # Add features
            for i, key in enumerate(keys):
                combination[key] = combo[i]["name"]
                if combo[i].get("trigger_phrase"):
                    combination[f"{key}_trigger"] = combo[i]["trigger_phrase"]
            
            # For each feature combination, generate angles
            # Use the first feature's images to determine angles
            first_feature = combo[0]
            if first_feature.get("images"):
                for image in first_feature["images"]:
                    angle_combo = combination.copy()
                    angle_combo["angle"] = image["angle"]
                    combinations.append(angle_combo)
            else:
                # Default angles if no images
                for angle in ["front", "side", "back"]:
                    angle_combo = combination.copy()
                    angle_combo["angle"] = angle
                    combinations.append(angle_combo)
        
        return combinations
    
    def _generate_caption(
        self, 
        ip_asset: IPAsset, 
        combination: Dict[str, str]
    ) -> str:
        """
        Generate caption for a training image.
        
        Format: {trigger_word}, {angle} view, {pose}, {outfit}, {expression}
        """
        parts = []
        
        # Add trigger word
        parts.append(ip_asset.trigger_word)
        
        # Add angle
        angle = combination.get("angle", "front")
        parts.append(f"{angle} view")
        
        # Add outfit if present
        if "outfit" in combination:
            outfit_trigger = combination.get("outfit_trigger")
            if outfit_trigger:
                parts.append(outfit_trigger)
            else:
                parts.append(f"wearing {combination['outfit']}")
        
        # Add expression if present
        if "expression" in combination:
            expr_trigger = combination.get("expression_trigger")
            if expr_trigger:
                parts.append(expr_trigger)
            else:
                parts.append(f"{combination['expression']} expression")
        
        # Add pose if present
        if "pose" in combination:
            pose_trigger = combination.get("pose_trigger")
            if pose_trigger:
                parts.append(pose_trigger)
            else:
                parts.append(f"{combination['pose']} pose")
        
        # Join with commas
        caption = ", ".join(parts)
        
        return caption
    
    async def preview_combinations(
        self,
        ip_asset_id: int,
        selected_features: Dict[str, List[int]],
    ) -> Dict[str, Any]:
        """
        Preview dataset combinations without creating dataset.
        
        Returns combination count and breakdown.
        """
        # Load features
        feature_data = {}
        for feature_type, feature_ids in selected_features.items():
            features = await self._load_features(feature_ids, feature_type)
            feature_data[feature_type] = features
        
        # Calculate combinations
        combinations = self._calculate_combinations(feature_data)
        
        # Generate sample captions
        ip_asset = await self.db.get(IPAsset, ip_asset_id)
        sample_captions = []
        for i, combo in enumerate(combinations[:5]):  # First 5
            caption = self._generate_caption(ip_asset, combo)
            sample_captions.append({
                "index": i + 1,
                "combination": combo,
                "caption": caption,
            })
        
        return {
            "total_images": len(combinations),
            "feature_breakdown": {
                ftype: len(feats) for ftype, feats in feature_data.items()
            },
            "sample_captions": sample_captions,
        }
