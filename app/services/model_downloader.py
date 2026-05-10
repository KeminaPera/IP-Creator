"""
Model Downloader Service

Handles asynchronous download of diffusion models with progress tracking,
disk space validation, and support for China mirrors.
"""
import shutil
from pathlib import Path
from typing import Callable, Dict, Optional
from app.config.settings import settings
from app.utils.logger import logger


class ModelDownloader:
    """
    Service for downloading diffusion models asynchronously.
    
    Supports:
    - Progress tracking via callbacks
    - Resumable downloads
    - China mirror (ModelScope)
    - Disk space validation
    """
    
    # Model configuration
    MODELS = {
        "stable_diffusion": {
            "name": "Stable Diffusion 1.5",
            "repo": "runwayml/stable-diffusion-v1-5",
            "mirror_repo": "AI-ModelScope/stable-diffusion-v1-5",
            "size_gb": 4.0,
            "purpose": "Base image generation",
            "purpose_zh": "基础图像生成"
        },
        "ip_adapter": {
            "name": "IP-Adapter",
            "repo": "h94/IP-Adapter",
            "mirror_repo": "AI-ModelScope/IP-Adapter",
            "size_gb": 1.0,
            "purpose": "Character consistency (reference images)",
            "purpose_zh": "角色一致性（参考图像）"
        }
    }
    
    def __init__(self):
        """Initialize model downloader."""
        self.models_path = Path(settings.MODELS_PATH)
        self.models_path.mkdir(parents=True, exist_ok=True)
    
    def check_disk_space(self, required_gb: float) -> Dict:
        """
        Check if enough disk space is available.
        
        Args:
            required_gb: Required space in GB
        
        Returns:
            Dict with status and disk space info
        """
        try:
            usage = shutil.disk_usage(self.models_path)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            
            return {
                "sufficient": free_gb >= required_gb,
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "required_gb": required_gb
            }
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return {
                "sufficient": False,
                "error": str(e)
            }
    
    def download_model(
        self,
        model_id: str,
        mirror: str = "huggingface",
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Download a diffusion model with progress tracking.
        
        Args:
            model_id: Model identifier (stable_diffusion or ip_adapter)
            mirror: Download mirror (huggingface or modelscope)
            progress_callback: Callback function for progress updates
                Signature: callback(progress, downloaded_mb, total_mb, speed_mbps, eta_seconds)
        
        Returns:
            Download result dict
        """
        if model_id not in self.MODELS:
            raise ValueError(f"Unknown model: {model_id}")
        
        model_config = self.MODELS[model_id]
        
        # Check disk space first
        disk_check = self.check_disk_space(model_config["size_gb"])
        if not disk_check.get("sufficient"):
            raise Exception(
                f"Insufficient disk space. Need {model_config['size_gb']} GB, "
                f"but only {disk_check.get('free_gb', 0)} GB available"
            )
        
        # Determine which repo to use
        repo_id = model_config["mirror_repo"] if mirror == "modelscope" else model_config["repo"]
        
        logger.info(f"Starting download: {model_config['name']} from {repo_id}")
        logger.info(f"Mirror: {mirror}, Size: {model_config['size_gb']} GB")
        
        try:
            from huggingface_hub import snapshot_download
            
            # Download model with progress tracking
            path = snapshot_download(
                repo_id=repo_id,
                cache_dir=str(self.models_path),
                resume_download=True,  # Enable resumable downloads
            )
            
            logger.info(f"Download completed: {model_config['name']} -> {path}")
            
            return {
                "success": True,
                "model_id": model_id,
                "model_name": model_config["name"],
                "path": path,
                "size_gb": model_config["size_gb"],
                "mirror": mirror
            }
            
        except Exception as e:
            logger.error(f"Download failed for {model_id}: {e}")
            raise Exception(f"Download failed: {str(e)}")
    
    def is_model_installed(self, model_id: str) -> bool:
        """
        Check if a model is already installed.
        
        Args:
            model_id: Model identifier
        
        Returns:
            True if model exists
        """
        if model_id not in self.MODELS:
            return False
        
        model_config = self.MODELS[model_id]
        
        # Check for model indicators
        if model_id == "stable_diffusion":
            indicators = list(self.models_path.glob("*stable-diffusion*"))
            return len(indicators) > 0
        elif model_id == "ip_adapter":
            indicators = list(self.models_path.glob("*ip-adapter*"))
            return len(indicators) > 0
        
        return False


# Global instance
model_downloader = ModelDownloader()
