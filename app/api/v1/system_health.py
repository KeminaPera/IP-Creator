"""
System Health Check API

Provides comprehensive system self-diagnosis including:
- Service connectivity (Redis, Database)
- Model availability (LLM, Diffusion, IP-Adapter)
- Configuration validation
- Resource status (GPU, disk space)
- Directory structure verification
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.config.database import get_db_session
from app.config.settings import settings
from app.models.llm_model import LLMConfig
from app.api.deps import get_current_user
from app.utils.response import success_response
from app.utils.logger import logger
from app.core.gpu_cache import gpu_cache

router = APIRouter(prefix="/api/v1/system", tags=["System Health"])


# Pydantic schemas for model download
class ModelDownloadRequest(BaseModel):
    """Request schema for model download."""
    model_id: str  # "stable_diffusion" or "ip_adapter"
    mirror: str = "huggingface"  # "huggingface" or "modelscope"


class HealthChecker:
    """System health checker utility."""
    
    @staticmethod
    def check_redis() -> Dict:
        """Check Redis connectivity with fast fail."""
        try:
            import redis
            # Set aggressive timeouts for health check
            r = redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=2,  # 2 seconds connection timeout
                socket_timeout=3           # 3 seconds operation timeout
            )
            r.ping()
            return {
                "status": "ok",
                "message": "Redis connected",
                "url": settings.REDIS_URL
            }
        except redis.exceptions.ConnectionError as e:
            return {
                "status": "error",
                "message": f"Redis connection failed: Connection refused or timeout (2s)",
                "url": settings.REDIS_URL,
                "impact": "Task queue will not work (image/video/story generation)"
            }
        except redis.exceptions.TimeoutError as e:
            return {
                "status": "error",
                "message": f"Redis connection timeout after 3 seconds",
                "url": settings.REDIS_URL,
                "impact": "Task queue will not work (image/video/story generation)"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Redis connection failed: {str(e)}",
                "url": settings.REDIS_URL,
                "impact": "Task queue will not work (image/video/story generation)"
            }
    
    @staticmethod
    async def check_database(session: AsyncSession) -> Dict:
        """Check database connectivity."""
        try:
            # Directly await the async operation - no need for run_until_complete
            await session.execute(select(func.count()))
            return {
                "status": "ok",
                "message": "Database connected",
                "url": settings.DATABASE_URL
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Database connection failed: {str(e)}",
                "url": settings.DATABASE_URL,
                "impact": "System cannot function"
            }
    
    @staticmethod
    async def check_llm_configs(session: AsyncSession) -> Dict:
        """Check LLM configurations."""
        try:
            # Query active configs
            result = await session.execute(
                select(LLMConfig).where(LLMConfig.is_active == True)
            )
            active_configs = result.scalars().all()
            
            # Query inactive configs
            result_inactive = await session.execute(
                select(LLMConfig).where(LLMConfig.is_active == False)
            )
            inactive_configs = result_inactive.scalars().all()
            
            if not active_configs and not inactive_configs:
                return {
                    "status": "warning",
                    "message": "No LLM configurations",
                    "count": 0,
                    "total": 0,
                    "active_ready": [],
                    "active_pending": [],
                    "inactive": []
                }
            
            # Build model info dict
            def build_model_info(config):
                return {
                    "id": config.id,
                    "name": config.name,
                    "provider": config.provider,
                    "model_name": config.model_name,
                    "model_type": config.model_type,
                    "health_status": config.health_status,
                    "response_time_ms": config.response_time_ms,
                    "success_rate": config.success_rate,
                    "last_health_check": config.last_health_check.isoformat() if config.last_health_check else None,
                    "has_api_key": bool(config.api_key_encrypted)
                }
            
            # Active - Ready (has API key for cloud, or local models)
            active_ready = [
                build_model_info(c) for c in active_configs
                if c.api_key_encrypted or c.model_type == "local"
            ]
            
            # Active - Pending (cloud models without API key)
            active_pending = [
                build_model_info(c) for c in active_configs
                if not c.api_key_encrypted and c.model_type == "cloud"
            ]
            
            # Inactive
            inactive = [build_model_info(c) for c in inactive_configs]
            
            ready_count = len(active_ready)
            
            return {
                "status": "ok" if ready_count > 0 else "warning",
                "message": f"{ready_count} LLM config(s) ready",
                "count": ready_count,
                "total": len(active_configs) + len(inactive_configs),
                "active_ready": active_ready,
                "active_pending": active_pending,
                "inactive": inactive
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check LLM configs: {str(e)}"
            }
    
    @staticmethod
    def check_directories() -> Dict:
        """Check required directories with detailed information."""
        # Extended directory configuration with descriptions
        required_dirs = {
            "STORAGE_PATH": {
                "path": settings.STORAGE_PATH,
                "description_zh": "主数据存储目录",
                "description_en": "Main data storage directory"
            },
            "IP_ASSETS_PATH": {
                "path": settings.IP_ASSETS_PATH,
                "description_zh": "IP资产图片存储（角色参考图）",
                "description_en": "IP asset images (character references)"
            },
            "LORA_MODELS_PATH": {
                "path": settings.LORA_MODELS_PATH,
                "description_zh": "LoRA微调模型存储",
                "description_en": "LoRA fine-tuned models"
            },
            "VIDEOS_PATH": {
                "path": settings.VIDEOS_PATH,
                "description_zh": "生成的视频文件存储",
                "description_en": "Generated video files"
            },
            "MODELS_PATH": {
                "path": settings.MODELS_PATH,
                "description_zh": "扩散模型存储（Stable Diffusion等）",
                "description_en": "Diffusion models (Stable Diffusion, etc.)"
            }
        }
        
        missing = []
        existing = []
        
        for name, config in required_dirs.items():
            p = Path(config["path"])
            dir_info = {
                "name": name,
                "path": str(p.absolute()),
                "description_zh": config["description_zh"],
                "description_en": config["description_en"],
                "exists": p.exists()
            }
            
            if p.exists():
                existing.append(dir_info)
            else:
                missing.append(dir_info)
                # Try to create
                try:
                    p.mkdir(parents=True, exist_ok=True)
                except:
                    pass
        
        if missing:
            return {
                "status": "warning",
                "message": f"{len(missing)} directory(ies) missing (auto-created)",
                "missing": missing,
                "existing": existing
            }
        
        return {
            "status": "ok",
            "message": "All directories exist",
            "directories": existing
        }
    
    @staticmethod
    def check_disk_space() -> Dict:
        """Check disk space availability."""
        try:
            storage_path = Path(settings.STORAGE_PATH)
            usage = shutil.disk_usage(storage_path.absolute())
            
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            
            status = "ok"
            message = f"{free_gb:.1f} GB free out of {total_gb:.1f} GB"
            
            if free_gb < 5:
                status = "error"
                message += " - CRITICAL: Low disk space!"
            elif free_gb < 10:
                status = "warning"
                message += " - Low disk space"
            
            return {
                "status": status,
                "message": message,
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_gb": round(usage.used / (1024**3), 2)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check disk space: {str(e)}"
            }
    
    @staticmethod
    def check_gpu() -> Dict:
        """Check GPU availability using cached GPU info."""
        try:
            # Use global GPU cache (lazy loading + caching)
            gpu_info = gpu_cache.get_info()
            
            # Return cached result in health check format
            return {
                "status": gpu_info["status"],
                "message": gpu_info["message"],
                "available": gpu_info["available"],
                "count": gpu_info["count"],
                "name": gpu_info.get("device_name"),
                "memory_gb": gpu_info["memory_gb"]
            }
        except Exception as e:
            logger.error(f"GPU check failed: {e}")
            return {
                "status": "error",
                "message": f"Failed to check GPU: {str(e)}",
                "available": False
            }
    
    @staticmethod
    def check_celery_worker() -> Dict:
        """Check if Celery worker is running with fast fail."""
        try:
            import redis
            # Set aggressive timeouts for health check
            r = redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=2,  # 2 seconds connection timeout
                socket_timeout=3           # 3 seconds operation timeout
            )
            
            # Check for Celery worker keys
            worker_keys = list(r.scan_iter("celery*"))
            
            if worker_keys:
                return {
                    "status": "ok",
                    "message": "Celery worker detected",
                    "active": True
                }
            else:
                return {
                    "status": "warning",
                    "message": "No Celery worker detected",
                    "active": False,
                    "impact": "Async tasks (generation, training) will not execute"
                }
        except redis.exceptions.ConnectionError as e:
            return {
                "status": "error",
                "message": f"Failed to check Celery: Redis connection refused or timeout (2s)",
                "active": False,
                "impact": "Cannot determine Celery status without Redis"
            }
        except redis.exceptions.TimeoutError as e:
            return {
                "status": "error",
                "message": f"Failed to check Celery: Redis timeout after 3 seconds",
                "active": False,
                "impact": "Cannot determine Celery status without Redis"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check Celery: {str(e)}",
                "active": False
            }
    
    @staticmethod
    def check_diffusion_models() -> Dict:
        """Check if diffusion models are available."""
        models_path = Path(settings.MODELS_PATH)
        
        # Define required models with download info
        required_models = {
            "stable_diffusion": {
                "name": "Stable Diffusion 1.5",
                "repo": "runwayml/stable-diffusion-v1-5",
                "size_gb": 4.0,
                "download_url": "https://huggingface.co/runwayml/stable-diffusion-v1-5",
                "purpose": "基础图像生成",
                "purpose_en": "Base image generation",
                "status": "unknown"
            },
            "ip_adapter": {
                "name": "IP-Adapter",
                "repo": "h94/IP-Adapter",
                "size_gb": 1.0,
                "download_url": "https://huggingface.co/h94/IP-Adapter",
                "purpose": "角色一致性（参考图像）",
                "purpose_en": "Character consistency (reference images)",
                "status": "unknown"
            }
        }
        
        # Check for existing models
        model_indicators = {
            "stable_diffusion": False,
            "ip_adapter": False,
            "lora_models": 0
        }
        
        if models_path.exists():
            # Look for model directories or files
            sd_indicators = list(models_path.glob("*stable-diffusion*"))
            ip_adapter_indicators = list(models_path.glob("*ip-adapter*"))
            lora_indicators = list(models_path.glob("*.safetensors"))
            
            model_indicators = {
                "stable_diffusion": len(sd_indicators) > 0,
                "ip_adapter": len(ip_adapter_indicators) > 0,
                "lora_models": len(lora_indicators)
            }
            
            # Update status for each model
            required_models["stable_diffusion"]["status"] = "installed" if model_indicators["stable_diffusion"] else "missing"
            required_models["ip_adapter"]["status"] = "installed" if model_indicators["ip_adapter"] else "missing"
        
        has_models = any([
            model_indicators.get("stable_diffusion", False),
            model_indicators.get("ip_adapter", False),
            model_indicators.get("lora_models", 0) > 0
        ])
        
        # Calculate total size needed
        total_size_needed = sum(
            model["size_gb"] for model in required_models.values() 
            if model["status"] == "missing"
        )
        
        if has_models:
            return {
                "status": "ok",
                "message": "Diffusion models detected",
                "models_path": str(models_path.absolute()),
                "models": model_indicators,
                "required_models": required_models,
                "total_size_needed_gb": total_size_needed
            }
        else:
            return {
                "status": "info",
                "message": "No local models found (will download on first use)",
                "models_path": str(models_path.absolute()),
                "models": model_indicators,
                "required_models": required_models,
                "total_size_needed_gb": total_size_needed,
                "note": "First generation will be slow due to model download"
            }
    
    @staticmethod
    def get_training_mode() -> Dict:
        """Check LoRA training mode."""
        mode = settings.LORA_TRAINING_MODE
        
        if mode == "mock":
            return {
                "status": "info",
                "message": "Mock training mode (for workflow validation)",
                "mode": "mock",
                "note": "Simulated training - no real model produced"
            }
        elif mode == "real":
            return {
                "status": "ok",
                "message": "Real training mode (Kohya)",
                "mode": "real",
                "requirement": "GPU with 8+ GB VRAM required"
            }
        else:
            return {
                "status": "warning",
                "message": f"Unknown training mode: {mode}",
                "mode": mode
            }


@router.get("/health")
async def system_health_check(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Comprehensive system health check.
    
    Checks all critical components and provides status report.
    """
    try:
        start_time = datetime.now()
        
        # Run all checks
        checks = {
            "redis": HealthChecker.check_redis(),
            "database": await HealthChecker.check_database(db),
            "llm_configs": await HealthChecker.check_llm_configs(db),
            "directories": HealthChecker.check_directories(),
            "disk_space": HealthChecker.check_disk_space(),
            "gpu": HealthChecker.check_gpu(),
            "celery_worker": HealthChecker.check_celery_worker(),
            "diffusion_models": HealthChecker.check_diffusion_models(),
            "training_mode": HealthChecker.get_training_mode(),
        }
        
        # Calculate overall status
        error_count = sum(1 for c in checks.values() if c.get("status") == "error")
        warning_count = sum(1 for c in checks.values() if c.get("status") == "warning")
        
        if error_count > 0:
            overall_status = "error"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        return success_response(
            data={
                "overall_status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "check_duration_seconds": round(elapsed, 3),
                "checks": checks,
                "summary": {
                    "total_checks": len(checks),
                    "errors": error_count,
                    "warnings": warning_count,
                    "healthy": len(checks) - error_count - warning_count
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return success_response(
            data={
                "overall_status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "checks": {}
            }
        )


@router.get("/health/summary")
async def health_summary(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Quick health summary (lightweight version).
    """
    try:
        checks = {
            "redis": HealthChecker.check_redis(),
            "llm_configs": await HealthChecker.check_llm_configs(db),
            "gpu": HealthChecker.check_gpu(),
            "celery_worker": HealthChecker.check_celery_worker(),
        }
        
        error_count = sum(1 for c in checks.values() if c.get("status") == "error")
        warning_count = sum(1 for c in checks.values() if c.get("status") == "warning")
        
        overall_status = "healthy"
        if error_count > 0:
            overall_status = "error"
        elif warning_count > 0:
            overall_status = "warning"
        
        return success_response(
            data={
                "overall_status": overall_status,
                "errors": error_count,
                "warnings": warning_count,
                "checks": checks
            }
        )
        
    except Exception as e:
        return success_response(
            data={
                "overall_status": "error",
                "error": str(e)
            }
        )


@router.post("/models/download")
async def start_model_download(
    request: ModelDownloadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start async model download via Celery.
    
    Returns immediately with task_id. Download runs in background.
    """
    from celery_worker import download_model_task
    from app.services.model_downloader import model_downloader
    
    # Validate model_id
    if request.model_id not in model_downloader.MODELS:
        return success_response(
            data={
                "success": False,
                "error": f"Unknown model: {request.model_id}"
            },
            status_code=400
        )
    
    # Check if already installed
    if model_downloader.is_model_installed(request.model_id):
        return success_response(
            data={
                "success": False,
                "error": "Model is already installed"
            },
            status_code=400
        )
    
    # Check disk space
    model_config = model_downloader.MODELS[request.model_id]
    disk_check = model_downloader.check_disk_space(model_config["size_gb"])
    
    if not disk_check.get("sufficient"):
        return success_response(
            data={
                "success": False,
                "error": f"Insufficient disk space. Need {model_config['size_gb']} GB, but only {disk_check.get('free_gb', 0)} GB available"
            },
            status_code=400
        )
    
    # Start async Celery task
    task = download_model_task.delay(
        model_id=request.model_id,
        mirror=request.mirror
    )
    
    return success_response(
        data={
            "success": True,
            "task_id": task.id,
            "model_id": request.model_id,
            "model_name": model_config["name"],
            "status": "queued",
            "message": f"Download started for {model_config['name']}"
        }
    )


@router.get("/models/download/{task_id}/status")
async def get_download_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get async download progress.
    
    Returns progress data without blocking.
    """
    from celery.result import AsyncResult
    
    task_result = AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        return success_response(
            data={
                "task_id": task_id,
                "status": "queued",
                "progress": 0
            }
        )
    elif task_result.state == 'PROGRESS':
        meta = task_result.info
        return success_response(
            data={
                "task_id": task_id,
                "status": "downloading",
                "progress": meta.get('progress', 0),
                "downloaded_mb": meta.get('downloaded_mb', 0),
                "total_mb": meta.get('total_mb', 0),
                "speed_mbps": meta.get('speed_mbps', 0),
                "eta_seconds": meta.get('eta_seconds', 0)
            }
        )
    elif task_result.state == 'SUCCESS':
        return success_response(
            data={
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "result": task_result.result
            }
        )
    elif task_result.state == 'FAILURE':
        return success_response(
            data={
                "task_id": task_id,
                "status": "failed",
                "error": str(task_result.result)
            }
        )
    else:
        return success_response(
            data={
                "task_id": task_id,
                "status": task_result.state.lower(),
                "progress": 0
            }
        )
