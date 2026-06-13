"""
IP Asset Manager Module

Manages IP character assets including image uploads, tag management,
style templates, and LoRA model associations.
"""
from typing import List, Optional, Dict, Any
from pathlib import Path
import shutil
from app.models.ip_asset import IPAsset
from app.schemas.ip_schema import IPAssetCreate, IPAssetUpdate, ImageReference
from app.config.settings import settings
from app.utils.logger import logger
from app.config.database import get_db_session_standalone
from sqlalchemy import select


# Style template presets
STYLE_TEMPLATES = {
    "3d_cartoon": {
        "name": "3D Cartoon",
        "description": "3D cartoon style with smooth surfaces and bright colors",
        "positive_tags": ["3d", "cartoon", "cute", "smooth", "colorful", "pixar style"],
        "negative_tags": ["realistic", "dark", "scary", "rough texture"],
    },
    "blind_box": {
        "name": "Blind Box Toy",
        "description": "Blind box toy style like Pop Mart",
        "positive_tags": ["blind box", "toy", "chibi", "kawaii", "pastel colors"],
        "negative_tags": ["realistic", "detailed", "mature"],
    },
    "healing": {
        "name": "Healing Minimalist",
        "description": "Soft, healing, minimalist style",
        "positive_tags": ["healing", "soft", "warm colors", "minimalist", "cozy"],
        "negative_tags": ["dark", "complex", "busy", "harsh"],
    },
    "warm_light": {
        "name": "Warm Soft Lighting",
        "description": "Warm yellow soft lighting style",
        "positive_tags": ["warm lighting", "soft shadows", "golden hour", "gentle"],
        "negative_tags": ["harsh lighting", "cold colors", "dark"],
    },
    "clean_background": {
        "name": "Clean Solid Background",
        "description": "Clean solid color background style",
        "positive_tags": ["solid background", "clean", "simple background", "studio"],
        "negative_tags": ["complex background", "cluttered", "busy"],
    },
}


class IPManager:
    """
    Service for managing IP character assets.
    
    Handles CRUD operations, image storage, tag management,
    and style template application.
    """
    
    def __init__(self):
        """Initialize IP manager."""
        self.assets_path = Path(settings.IP_ASSETS_PATH)
        self.assets_path.mkdir(parents=True, exist_ok=True)
    
    async def create_ip_asset(self, ip_data: IPAssetCreate) -> IPAsset:
        """
        Create a new IP asset.
        
        Args:
            ip_data: IP asset creation data
            
        Returns:
            Created IP asset
        """
        async with get_db_session_standalone() as session:
            # Process reference images
            ref_images = []
            for img in ip_data.reference_images or []:
                if isinstance(img, dict):
                    ref_images.append(img)
                elif isinstance(img, ImageReference):
                    ref_images.append(img.model_dump())
                elif isinstance(img, str):
                    # If it's just a path string, create a dict
                    ref_images.append({"angle": "front", "path": img})
                else:
                    ref_images.append(img)
            
            # Create IP asset record
            ip_asset = IPAsset(
                name=ip_data.name,
                category=ip_data.category,
                description=ip_data.description,
                trigger_word=ip_data.trigger_word,
                style_template=ip_data.style_template,
                reference_images=ref_images,
                positive_tags=ip_data.positive_tags,
                negative_tags=ip_data.negative_tags,
                lora_model_id=ip_data.lora_model_id,
            )
            
            session.add(ip_asset)
            await session.commit()
            await session.refresh(ip_asset)
            
            logger.info(f"Created IP asset: {ip_asset.name}")
            return ip_asset
    
    async def get_ip_asset(self, ip_id: int) -> Optional[IPAsset]:
        """
        Get IP asset by ID.
        
        Args:
            ip_id: IP asset ID
            
        Returns:
            IP asset or None
        """
        async with get_db_session_standalone() as session:
            result = await session.execute(
                select(IPAsset).where(IPAsset.id == ip_id)
            )
            return result.scalar_one_or_none()
    
    async def list_ip_assets(
        self,
        skip: int = 0,
        limit: int = 20,
        category: Optional[str] = None,
    ) -> tuple[List[IPAsset], int]:
        """
        List IP assets with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records
            category: Filter by category
            
        Returns:
            Tuple of (IP assets list, total count)
        """
        async with get_db_session_standalone() as session:
            query = select(IPAsset)
            
            if category:
                query = query.where(IPAsset.category == category)
            
            # Get total count
            count_query = select(IPAsset)
            if category:
                count_query = count_query.where(IPAsset.category == category)
            total_result = await session.execute(count_query)
            total = len(total_result.scalars().all())
            
            # Get paginated results
            query = query.offset(skip).limit(limit)
            result = await session.execute(query)
            items = result.scalars().all()
            
            return items, total
    
    async def update_ip_asset(
        self,
        ip_id: int,
        ip_data: IPAssetUpdate,
    ) -> Optional[IPAsset]:
        """
        Update an IP asset.
        
        Args:
            ip_id: IP asset ID
            ip_data: Update data
            
        Returns:
            Updated IP asset or None
        """
        async with get_db_session_standalone() as session:
            ip_asset = await session.get(IPAsset, ip_id)
            if not ip_asset:
                return None
            
            update_data = ip_data.dict(exclude_unset=True)
            
            # Handle reference images conversion
            if "reference_images" in update_data:
                update_data["reference_images"] = [
                    img.dict() if isinstance(img, ImageReference) else img
                    for img in update_data["reference_images"]
                ]
            
            for key, value in update_data.items():
                setattr(ip_asset, key, value)
            
            await session.commit()
            await session.refresh(ip_asset)
            
            logger.info(f"Updated IP asset: {ip_asset.name}")
            return ip_asset
    
    async def delete_ip_asset(self, ip_id: int) -> bool:
        """
        Delete an IP asset.
        
        Args:
            ip_id: IP asset ID
            
        Returns:
            True if deleted successfully
        """
        async with get_db_session_standalone() as session:
            ip_asset = await session.get(IPAsset, ip_id)
            if not ip_asset:
                return False
            
            # Delete associated images
            for img_ref in ip_asset.reference_images:
                img_path = Path(img_ref["path"])
                if img_path.exists():
                    img_path.unlink()
            
            await session.delete(ip_asset)
            await session.commit()
            
            logger.info(f"Deleted IP asset: {ip_asset.name}")
            return True
    
    def apply_style_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        Get style template presets.
        
        Args:
            template_name: Template name
            
        Returns:
            Template configuration or None
        """
        return STYLE_TEMPLATES.get(template_name)
    
    def get_all_style_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available style templates.
        
        Returns:
            Dictionary of all style templates
        """
        return STYLE_TEMPLATES


# Global IP manager instance
ip_manager = IPManager()
