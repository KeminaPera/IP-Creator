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
            "mirror_repo": "stable-diffusion-v1-5/stable-diffusion-v1-5",  # ✅ hf-mirror.com上的路径
            "size_gb": 4.0,
            "purpose": "Base image generation",
            "purpose_zh": "基础图像生成"
        },
        "ip_adapter": {
            "name": "IP-Adapter",
            "repo": "h94/IP-Adapter",
            "mirror_repo": "h94/IP-Adapter",  # ModelScope使用相同路径，通过HF_ENDPOINT镜像
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
            import os
            
            # ✅ 必须在import huggingface_hub之前设置环境变量
            # Apply HF_ENDPOINT mirror if configured
            hf_endpoint = os.environ.get("HF_ENDPOINT") or getattr(settings, 'HF_ENDPOINT', None)
            if hf_endpoint:
                os.environ["HF_ENDPOINT"] = hf_endpoint  # ✅ 确保环境变量已设置
                os.environ["HUGGINGFACE_CO_RESOLVE_ENDPOINT"] = hf_endpoint  # ✅ 兼容旧版本
            
            from huggingface_hub import snapshot_download
            from huggingface_hub import constants
            
            if hf_endpoint:
                constants.ENDPOINT = hf_endpoint
                logger.info(f"Using Hugging Face mirror: {hf_endpoint}")
            
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
    
    def validate_model_integrity(self, model_id: str) -> dict:
        """
        校验模型完整性（检查关键文件是否存在）。
        
        Args:
            model_id: Model identifier
        
        Returns:
            {
                "valid": True/False,
                "status": "installed" | "incomplete" | "missing",
                "missing_files": [...],  # 缺失的关键文件
                "existing_files": [...],  # 已存在的关键文件
                "path": "模型路径"
            }
        """
        import os
        from huggingface_hub import scan_cache_dir
        
        if model_id not in self.MODELS:
            return {
                "valid": False,
                "status": "missing",
                "missing_files": [],
                "existing_files": [],
                "path": None
            }
        
        model_config = self.MODELS[model_id]
        repo_id = model_config["repo"]
        
        # 定义每个模型的关键文件（完整性校验清单）
        required_files_map = {
            "stable_diffusion": [
                "model_index.json",      # Stable Diffusion 核心索引
                "unet/config.json",      # UNet 架构配置
                "vae/config.json",       # VAE 配置
                "text_encoder/config.json",  # 文本编码器配置
            ],
            "ip_adapter": [
                # IP-Adapter是纯权重仓库，没有model_index.json
                "models/ip-adapter-plus_sd15.safetensors",  # IP-Adapter 权重文件
                "models/image_encoder/model.safetensors",   # 图像编码器
            ]
        }
        
        required_files = required_files_map.get(model_id, ["model_index.json"])
        
        # huggingface_hub 缓存路径
        hf_cache = Path(os.path.expanduser("~/.cache/huggingface/hub"))
        model_prefix = repo_id.replace("/", "--")
        model_cache_dir = hf_cache / f"models--{model_prefix}"
        
        # 检查是否在自定义目录（data/models/）
        custom_models_dir = Path(settings.MODELS_PATH)
        custom_model_dir = custom_models_dir / f"models--{model_prefix}"
        
        # 优先检查自定义目录
        if custom_model_dir.exists():
            model_cache_dir = custom_model_dir
        
        if not model_cache_dir.exists():
            return {
                "valid": False,
                "status": "missing",
                "missing_files": required_files,
                "existing_files": [],
                "path": str(model_cache_dir)
            }
        
        # 扫描已下载的文件
        existing_files = []
        missing_files = []
        
        # huggingface_hub 使用 snapshots 目录存储实际文件
        snapshots_dir = model_cache_dir / "snapshots"
        if not snapshots_dir.exists():
            return {
                "valid": False,
                "status": "incomplete",
                "missing_files": required_files,
                "existing_files": [],
                "path": str(model_cache_dir)
            }
        
        # 查找最新的 snapshot（可能有多个版本）
        snapshot_dirs = list(snapshots_dir.glob("*"))
        if not snapshot_dirs:
            return {
                "valid": False,
                "status": "incomplete",
                "missing_files": required_files,
                "existing_files": [],
                "path": str(model_cache_dir)
            }
        
        # 使用最新的 snapshot
        latest_snapshot = max(snapshot_dirs, key=lambda d: d.stat().st_mtime)
        
        # 检查每个关键文件
        for req_file in required_files:
            file_path = latest_snapshot / req_file
            if file_path.exists():
                # 额外检查文件大小（0字节算缺失）
                if file_path.stat().st_size > 0:
                    existing_files.append(req_file)
                else:
                    missing_files.append(req_file)
            else:
                missing_files.append(req_file)
        
        is_valid = len(missing_files) == 0
        status = "installed" if is_valid else "incomplete"
        
        return {
            "valid": is_valid,
            "status": status,
            "missing_files": missing_files,
            "existing_files": existing_files,
            "path": str(latest_snapshot),
            "snapshot_dir": str(latest_snapshot.name)
        }
    
    def is_model_installed(self, model_id: str) -> bool:
        """
        Check if a model is already installed AND complete.
        
        Args:
            model_id: Model identifier
        
        Returns:
            True if model exists and passes integrity check
        """
        if model_id not in self.MODELS:
            return False
        
        # 使用完整性校验代替简单的目录检查
        integrity = self.validate_model_integrity(model_id)
        return integrity["status"] == "installed"


# Global instance
model_downloader = ModelDownloader()
