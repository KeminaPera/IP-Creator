"""
Storage Service

Handles file uploads, downloads, and media storage for generated content.
"""
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile
from app.config.settings import settings
from app.utils.logger import logger


class StorageService:
    """
    Service for file storage operations.
    
    Manages uploaded reference images, generated images, videos,
    and trained LoRA models.
    """
    
    def __init__(self):
        """Initialize storage paths."""
        self.storage_path = Path(settings.STORAGE_PATH)
        self.ip_assets_path = Path(settings.IP_ASSETS_PATH)
        self.videos_path = Path(settings.VIDEOS_PATH)
        self.lora_models_path = Path(settings.LORA_MODELS_PATH)
        self.models_path = Path(settings.MODELS_PATH)
        
        # Ensure directories exist
        for path in [self.ip_assets_path, self.videos_path, 
                     self.lora_models_path, self.models_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, original_filename: str, prefix: str = "") -> str:
        """Generate a unique filename."""
        ext = Path(original_filename).suffix
        unique_id = str(uuid.uuid4())[:8]
        return f"{prefix}{unique_id}{ext}"
    
    async def save_upload_file(
        self, 
        upload_file: UploadFile, 
        directory: str = "ip_assets",
        prefix: str = ""
    ) -> Tuple[str, str]:
        """
        Save an uploaded file to storage.
        
        Args:
            upload_file: FastAPI UploadFile
            directory: Target directory name
            prefix: Filename prefix
            
        Returns:
            Tuple of (file_path, file_url)
        """
        target_dir = self.storage_path / directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filename = self._generate_filename(upload_file.filename or "upload", prefix)
        file_path = target_dir / filename
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            
            file_url = f"/api/v1/files/{directory}/{filename}"
            logger.info(f"Saved upload file: {file_path}")
            return str(file_path), file_url
            
        except Exception as e:
            logger.error(f"Failed to save upload file: {e}")
            raise
        finally:
            upload_file.file.close()
    
    async def save_generated_image(
        self, 
        image_data: bytes, 
        ip_asset_id: int,
        ext: str = ".png"
    ) -> Tuple[str, str]:
        """
        Save a generated image.
        
        Args:
            image_data: Raw image bytes
            ip_asset_id: Associated IP asset ID
            ext: File extension
            
        Returns:
            Tuple of (file_path, file_url)
        """
        target_dir = self.videos_path / "images" / f"ip_{ip_asset_id}"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = target_dir / filename
        
        try:
            with open(file_path, "wb") as f:
                f.write(image_data)
            
            file_url = f"/api/v1/files/images/ip_{ip_asset_id}/{filename}"
            logger.info(f"Saved generated image: {file_path}")
            return str(file_path), file_url
            
        except Exception as e:
            logger.error(f"Failed to save generated image: {e}")
            raise
    
    async def save_generated_video(
        self,
        video_data: bytes,
        ip_asset_id: int,
        ext: str = ".mp4"
    ) -> Tuple[str, str]:
        """
        Save a generated video.
        
        Args:
            video_data: Raw video bytes
            ip_asset_id: Associated IP asset ID
            ext: File extension
            
        Returns:
            Tuple of (file_path, file_url)
        """
        target_dir = self.videos_path / "videos" / f"ip_{ip_asset_id}"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = target_dir / filename
        
        try:
            with open(file_path, "wb") as f:
                f.write(video_data)
            
            file_url = f"/api/v1/files/videos/ip_{ip_asset_id}/{filename}"
            logger.info(f"Saved generated video: {file_path}")
            return str(file_path), file_url
            
        except Exception as e:
            logger.error(f"Failed to save generated video: {e}")
            raise
    
    def get_file_path(self, directory: str, filename: str) -> Optional[Path]:
        """Get the full path of a stored file."""
        file_path = self.storage_path / directory / filename
        if file_path.exists():
            return file_path
        return None
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a stored file."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False


# Global storage service instance
storage_service = StorageService()
