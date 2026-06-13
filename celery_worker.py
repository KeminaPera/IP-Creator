"""Celery Worker Configuration

Defines all asynchronous task definitions for background processing
including LLM calls, LoRA training, and video generation.
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# ✅ 确保项目根目录在 sys.path 中（Celery worker 任务执行时需要导入 flowpipe 等本地模块）
_PROJECT_ROOT = str(Path(__file__).resolve().parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
from celery import Celery
from celery.signals import worker_process_init, worker_ready
from app.config.settings import settings
from typing import Optional
from sqlalchemy import update

logger = logging.getLogger(__name__)

# ✅ 设置 HuggingFace 缓存路径环境变量（Celery Worker 进程也需要）
HF_HUB_CACHE_PATH = Path(settings.HF_HUB_CACHE_PATH).resolve()
os.environ.setdefault('HF_HUB_CACHE', str(HF_HUB_CACHE_PATH))

# ✅ 将 Celery 任务 ID 设置为 traceId（实现分布式链路追踪）
from celery.signals import task_prerun, task_postrun

@task_prerun.connect
def bind_celery_task_id_as_trace_id(sender=None, task_id=None, **kwargs):
    """
    在 Celery 任务执行前，将任务 ID 设置为 traceId。
    
    这样任务执行过程中的所有日志都会自动包含任务 ID 作为 traceId，
    实现完整的分布式链路追踪。
    """
    if task_id:
        # 延迟导入避免循环依赖
        from app.core.trace import set_trace_id
        set_trace_id(task_id)
        logger.debug(f"Trace ID set to Celery task ID: {task_id}")

@task_postrun.connect
def clear_trace_id_after_task(sender=None, task_id=None, **kwargs):
    """任务执行完成后清除 traceId（避免污染后续任务）"""
    from app.core.trace import set_trace_id
    set_trace_id("")
    logger.debug(f"Trace ID cleared after task: {task_id}")

# Eager-import all ORM models so SQLAlchemy mappers can resolve string-based
# relationships (e.g. LoRAModel.quality_reports -> 'QualityReport') in workers.
from app.models import (  # noqa: F401
    user, ip_asset, llm_model, llm_provider, lora_model,
    task, generated_content, system_setting, quality_report,
)

# Task modules are defined directly in this file

# =============================================================================
# Helper Functions
# =============================================================================

def update_task_status(task_id: str, status: str, progress: int = 0, 
                       started_at=None, completed_at=None, error_message=None):
    """
    Update task status using connection pool with automatic rollback.
    
    Args:
        task_id: Celery task ID
        status: New status (running, completed, failed)
        progress: Progress percentage (0-100)
        started_at: datetime object or None
        completed_at: datetime object or None
        error_message: Error message or None
    """
    from app.config.database import get_sync_session_safe
    from app.models.task import TaskRecord
    
    values = {'status': status, 'progress': progress}
    if started_at:
        values['started_at'] = started_at
    if completed_at:
        values['completed_at'] = completed_at
    if error_message:
        values['error_message'] = error_message
    
    with get_sync_session_safe() as session:
        session.execute(
            update(TaskRecord)
            .where(TaskRecord.task_id == task_id)
            .values(**values)
        )


# =============================================================================
# Celery 队列 SSOT (Single Source of Truth)
# -----------------------------------------------------------------------------
# CELERY_QUEUES: worker 必须监听的全部队列, 启动脚本通过 import 此常量派生 -Q 参数
#                (start_celery.sh / start_celery.bat / docker-compose.yml 都读这里)
# TASK_ROUTES  : 任务名 -> 队列 的路由映射, 任何使用的 queue 必须出现在 CELERY_QUEUES 中
# 修改时务必两个变量同步, worker_ready 信号会在启动时做一致性校验.
#
# ⚠️  重要：不要手动在启动命令中指定 -Q 参数！
#          使用启动脚本，它会自动读取 CELERY_QUEUES 常量：
#          - macOS/Linux: ./start_celery.sh
#          - Windows:     start_celery.bat
#          - Docker:      docker-compose up (已配置动态读取)
#          手动指定极易导致队列遗漏和不一致！
# =============================================================================
CELERY_QUEUES = [
    "celery",              # 默认队列 (兼容未路由任务)
    "story_generation",    # 文本 / 剧本生成
    "image_generation",    # 图像生成
    "video_generation",    # 视频生成
    "lora_training",       # LoRA 训练
]

TASK_ROUTES = {
    "celery_worker.generate_image_task": {"queue": "image_generation"},
    "celery_worker.generate_story_task": {"queue": "story_generation"},
    "celery_worker.generate_video_task": {"queue": "video_generation"},
    "celery_worker.download_model_task": {"queue": "celery"},  # 下载任务走默认队列
    "celery_worker.train_lora_task": {"queue": "lora_training"},  # LoRA训练任务走lora_training队列
    "celery_worker.execute_workflow_task": {"queue": "image_generation"},  # FlowPipe工作流任务
}

# Celery application instance
celery_app = Celery(
    "ip_creator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task routing (queue names must be present in CELERY_QUEUES)
    task_routes=TASK_ROUTES,
    
    # Concurrency settings
    worker_concurrency=settings.MAX_CONCURRENT_TASKS,
    worker_prefetch_multiplier=1,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Retry settings
    task_default_retry_delay=60,
    task_default_max_retries=3,
    
    # Result expiration
    result_expires=3600,
)


@worker_ready.connect
def _verify_queue_consistency(sender=None, **kwargs):
    """启动后校验 worker 监听队列 ⊇ task_routes 路由的队列集合。"""
    try:
        listening = {q.name for q in sender.task_consumer.queues}
        routed = {v["queue"] for v in TASK_ROUTES.values()}
        missing = routed - listening
        if missing:
            logger.warning(
                f"Task routes routing to {sorted(missing)} "
                f"but worker not listening! Check -Q parameter. "
                f"(Currently listening: {sorted(listening)})"
            )
        else:
            logger.info(f"Queue consistency check passed, listening {sorted(listening)}")
    except Exception as e:
        logger.error(f"Queue consistency check exception: {e}")


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize worker process: event loop + GPU cache + LLM manager."""
    try:
        # 创建全局事件循环（所有任务复用）
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 清除GPU缓存，确保worker进程重新检测MPS设备
        from app.core.gpu_cache import gpu_cache
        gpu_cache.invalidate()
        
        from app.core.llm_manager import llm_manager
        loop.run_until_complete(llm_manager.initialize_models())
        logger.info(f"LLM manager initialized, active model: {llm_manager.registry.get_active_model_id()}")
    except Exception as e:
        logger.error(f"Failed to initialize LLM manager: {e}")


def create_content_record(
    task_id: str,
    task_type: str,
    content_type: str,
    result_data: dict,
    execution_time: float = None
):
    """
    Create a GeneratedContent record after successful task completion.
    
    Args:
        task_id: Celery task ID
        task_type: Type of task (story_generation, image_generation, video_generation)
        content_type: Type of content (story, image, video)
        result_data: Result data from generation task
        execution_time: Execution time in seconds
    """
    try:
        import json
        from datetime import datetime
        from pathlib import Path
        from app.config.database import get_sync_session_safe
        from app.models.generated_content import GeneratedContent
        
        # Extract metadata from result
        title = result_data.get('title', f"{content_type.capitalize()} - {task_id[:8]}")
        description = result_data.get('description', '')
        file_path = result_data.get('file_path', result_data.get('output_path', ''))
        ip_asset_id = result_data.get('ip_asset_id')
        channel_id = result_data.get('channel_id')
        
        # Generate thumbnail for images and videos
        thumbnail_path = None
        if content_type == 'image' and file_path:
            thumbnail_path = generate_image_thumbnail(file_path)
        elif content_type == 'video' and file_path:
            thumbnail_path = generate_video_thumbnail(file_path)
        
        # Build content-specific metadata
        content_metadata = {
            'model': result_data.get('model', ''),
            'channel_id': channel_id,
            'generation_params': result_data.get('params', {})
        }
        
        # Media-specific fields
        duration_seconds = result_data.get('duration_seconds')
        resolution = result_data.get('resolution')
        word_count = result_data.get('word_count')
        file_size = result_data.get('file_size')
        
        # Parameters used for generation
        parameters = result_data.get('params', result_data.get('input_params', {}))
        
        # Use connection pool with auto commit/rollback
        with get_sync_session_safe() as session:
            content = GeneratedContent(
                task_id=task_id,
                task_type=task_type,
                content_type=content_type,
                title=title,
                description=description,
                file_path=file_path,
                thumbnail_path=thumbnail_path,
                file_size=file_size,
                duration_seconds=duration_seconds,
                resolution=resolution,
                word_count=word_count,
                ip_asset_id=ip_asset_id,
                parameters=parameters if parameters else None,
                content_metadata=content_metadata,
                status='completed',
                execution_time_seconds=execution_time,
                channel_id=channel_id
            )
            session.add(content)
        
        logger.info(f"Created content record: {content_type} - {title} (ID: {task_id})")
        
    except Exception as e:
        logger.error(f"Failed to create content record: {e}")


def generate_image_thumbnail(image_path: str, thumb_size: tuple = (300, 300)) -> str:
    """
    Generate thumbnail for an image.
    
    Args:
        image_path: Path to original image
        thumb_size: Thumbnail size (width, height)
    
    Returns:
        Path to generated thumbnail, or None if failed
    """
    try:
        from PIL import Image
        from pathlib import Path
        
        original = Path(image_path)
        if not original.exists():
            return None
        
        # Create thumbnail path
        thumb_dir = original.parent / 'thumbnails'
        thumb_dir.mkdir(exist_ok=True)
        thumb_path = thumb_dir / f"thumb_{original.name}"
        
        # Generate thumbnail
        with Image.open(original) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=85)
        
        return str(thumb_path)
    except Exception as e:
        logger.error(f"Failed to generate image thumbnail: {e}")
        return None


def generate_video_thumbnail(video_path: str, timestamp: str = '00:00:01') -> str:
    """
    Generate thumbnail for a video by extracting a frame.
    
    Args:
        video_path: Path to original video
        timestamp: Timestamp to extract frame from (HH:MM:SS)
    
    Returns:
        Path to generated thumbnail, or None if failed
    """
    try:
        import subprocess
        from pathlib import Path
        
        original = Path(video_path)
        if not original.exists():
            return None
        
        # Create thumbnail path
        thumb_dir = original.parent / 'thumbnails'
        thumb_dir.mkdir(exist_ok=True)
        thumb_path = thumb_dir / f"thumb_{original.stem}.jpg"
        
        # Use ffmpeg to extract frame
        result = subprocess.run([
            'ffmpeg',
            '-i', str(original),
            '-ss', timestamp,
            '-vframes', '1',
            '-y',  # Overwrite output file
            str(thumb_path)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and thumb_path.exists():
            return str(thumb_path)
        else:
            logger.error(f"FFmpeg failed: {result.stderr}")
            return None
    except FileNotFoundError:
        logger.warning("FFmpeg not installed, skipping video thumbnail generation")
        return None
    except Exception as e:
        logger.error(f"Failed to generate video thumbnail: {e}")
        return None


@celery_app.task(bind=True, max_retries=3)
def generate_story_task(self, prompt: str, ip_name: Optional[str] = None, ip_asset_id: Optional[int] = None, style: Optional[str] = None, duration: int = 10, channel_id: Optional[int] = None) -> dict:
    """Async story generation task."""
    import time
    from datetime import datetime
    start_time = time.time()
    
    try:
        import asyncio
        from app.core.video_generator import video_generator
        
        # Update task status to running
        update_task_status(self.request.id, 'running', 10, started_at=datetime.now())
        
        # 在Celery子线程中显式创建事件循环（避免'There is no current event loop'错误）
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 子线程中没有事件循环，需要创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            video_generator.generate_story(
                prompt=prompt,
                ip_name=ip_name,
                style=style,
                duration_seconds=duration,
                channel_id=channel_id,
            )
        )
        
        if result["status"] == "failed":
            # Update task status to failed
            update_task_status(self.request.id, 'failed', 0)
            raise Exception(result.get("error", "Story generation failed"))
        
        # Update task status to completed
        update_task_status(
            self.request.id, 'completed', 100,
            completed_at=datetime.now()
        )
        
        # Create content record with complete metadata
        execution_time = time.time() - start_time
        
        # Enrich result_data with additional metadata
        result_data = {
            **result,
            'ip_asset_id': ip_asset_id,
            'channel_id': channel_id,
            'params': {
                'prompt': prompt,
                'ip_name': ip_name,
                'style': style,
                'duration': duration,
            }
        }
        
        create_content_record(
            task_id=self.request.id,
            task_type='story_generation',
            content_type='story',
            result_data=result_data,
            execution_time=execution_time
        )
        
        return {"status": "success", "data": result}
    
    except Exception as exc:
        # Update task status to failed on error
        try:
            update_task_status(self.request.id, 'failed', 0)
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=2)
def generate_image_task(self, prompt: str, ip_asset_id: int = 0, **kwargs) -> dict:
    """Async image generation task with Diffusers."""
    import time
    from datetime import datetime
    start_time = time.time()
    
    try:
        import asyncio
        from app.core.video_generator import video_generator
        
        # Update task status to running
        update_task_status(self.request.id, 'running', 10, started_at=datetime.now())
        
        # 在Celery子线程中显式创建事件循环（避免'There is no current event loop'错误）
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 子线程中没有事件循环，需要创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 从 kwargs 中提取 view_type（不传给 video_generator）
        view_type = kwargs.pop('view_type', None)
        
        # 从 kwargs 中移除 generate_image 不接受的参数
        kwargs.pop('seed', None)  # seed 不被 generate_image 接受
        
        result = loop.run_until_complete(
            video_generator.generate_image(
                prompt=prompt,
                ip_asset_id=ip_asset_id,
                **kwargs  # 不再包含 view_type
            )
        )
        
        if result["status"] == "failed":
            error_msg = result.get("error", "Image generation failed")
            
            # Update task status to failed with error message
            update_task_status(
                self.request.id, 'failed', 0,
                completed_at=datetime.now(),
                error_message=error_msg
            )
            logger.error(f"Task {self.request.id} failed: {error_msg}")
            raise Exception(error_msg)
        
        # Update task status to completed
        execution_time = time.time() - start_time
        update_task_status(
            self.request.id, 'completed', 100,
            completed_at=datetime.now()
        )
        
        # Auto-trigger IP consistency check if using IP-Adapter
        try:
            use_ip_adapter = kwargs.get('use_ip_adapter', False)
            reference_images = kwargs.get('reference_images', [])
            
            if use_ip_adapter and reference_images and ip_asset_id:
                import asyncio
                from app.services.ip_adapter_service import IPAdapterService
                
                async def run_consistency_check():
                    ip_adapter_service = IPAdapterService()
                    generated_image_path = result.get('image_path') or result.get('file_path')
                    
                    if generated_image_path:
                        consistency_result = await ip_adapter_service.check_generated_consistency(
                            generated_image_path=generated_image_path,
                            reference_images=reference_images
                        )
                        
                        # Log consistency score
                        score = consistency_result.get('consistency_score', 0)
                        logger.info(f"IP consistency check: {score}/100 for task {self.request.id}")
                        
                        # If score is low, add warning to result
                        if score < 80:
                            result['consistency_warning'] = f"IP consistency score is low: {score}/100"
                
                # Run check in background（使用当前事件循环）
                try:
                    current_loop = asyncio.get_event_loop()
                    current_loop.create_task(run_consistency_check())
                except RuntimeError:
                    # 如果没有运行中的事件循环，同步执行
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(run_consistency_check())
                    loop.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Auto consistency check failed: {e}")
        
        # Create content record with complete metadata
        execution_time = time.time() - start_time
        
        # Enrich result_data with additional metadata
        result_data = {
            **result,
            'ip_asset_id': ip_asset_id,
            'channel_id': kwargs.get('channel_id'),
        }
        
        create_content_record(
            task_id=self.request.id,
            task_type='image_generation',
            content_type='image',
            result_data=result_data,
            execution_time=execution_time
        )
        
        # Create IPMultiView record (for three-view generation)
        try:
            file_path = result.get("file_path") or result.get("image_path")
            # view_type 已在第507行提取为局部变量，直接使用
            
            if view_type and ip_asset_id and file_path:
                try:
                    from app.models.ip_multi_view import IPMultiView
                    from app.config.database import get_sync_session_safe
                    
                    # Get consistency score from result
                    consistency_score = result.get('consistency_score', 0)
                    
                    with get_sync_session_safe() as session:
                        multi_view = IPMultiView(
                            ip_asset_id=ip_asset_id,
                            view_type=view_type,  # Table field: for query/sort/display
                            image_path=file_path,
                            source="generated",
                            generation_params={  # JSON field: for parameter tracing/reproduction
                                "prompt": prompt,
                                "view_type": view_type,  # For tracing what view_type was used
                                "negative_prompt": kwargs.get('negative_prompt', ''),
                                "seed": kwargs.get('seed'),
                                "steps": kwargs.get('steps', 30),
                                "cfg_scale": kwargs.get('cfg_scale', 7.0),
                                "ip_adapter_scale": kwargs.get('ip_adapter_scale', 0.85),
                                "ip_adapter_mode": os.environ.get(
                                    "IP_ADAPTER_MODE",
                                    getattr(settings, "IP_ADAPTER_MODE", "original"),
                                ),
                                "lora_weight": kwargs.get('lora_weight', 0.7),
                                "lora_path": kwargs.get('lora_path'),
                                "use_ip_adapter": kwargs.get('use_ip_adapter', False),
                                "reference_images": kwargs.get('reference_images', []),
                                "width": kwargs.get('width', 512),
                                "height": kwargs.get('height', 512),
                                "generation_time": execution_time,
                            },
                            quality_score=consistency_score,
                            is_primary=(view_type == "front"),
                        )
                        session.add(multi_view)
                        
                        logger.info(f"Created IPMultiView for IP {ip_asset_id}, view {view_type}")
                except Exception as e:
                    logger.error(f"Failed to create IPMultiView: {e}", exc_info=True)
                    # Don't fail the task if IPMultiView creation fails
        except Exception as e:
            logger.warning(f"IPMultiView creation skipped: {e}")
        
        return {"status": "success", "data": result}
    
    except Exception as exc:
        # Only retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120)
        else:
            # Final retry failed, update task status with detailed error info
            import traceback
            error_msg = str(exc)
            error_details = (
                f"Task ID: {self.request.id}\n"
                f"IP Asset ID: {ip_asset_id}\n"
                f"View Type: {view_type or 'unknown'}\n"
                f"Prompt: {prompt[:100]}...\n"
                f"Parameters: {kwargs}\n"
                f"Error: {error_msg}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            
            update_task_status(
                self.request.id, 'failed', 0,
                completed_at=datetime.now(),
                error_message=error_details
            )
            logger.error(
                f"Task {self.request.id} permanently failed after {self.max_retries} retries:\n"
                f"  IP Asset ID: {ip_asset_id}\n"
                f"  View Type: {view_type or 'unknown'}\n"
                f"  Error: {error_msg}",
                exc_info=True
            )
            return {"status": "failed", "error": error_msg}


@celery_app.task(bind=True, max_retries=1)
def generate_video_task(self, prompt: str, image_path: str, ip_asset_id: int = 0, **kwargs) -> dict:
    """Async video generation task with Diffusers."""
    import time
    from datetime import datetime
    
    start_time = time.time()
    
    try:
        import asyncio
        from app.core.video_generator import video_generator
        
        # Update task status to running
        update_task_status(self.request.id, 'running', 10, started_at=datetime.now())
        
        # 在Celery子线程中显式创建事件循环（避免'There is no current event loop'错误）
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 子线程中没有事件循环，需要创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            video_generator.generate_video(
                prompt=prompt,
                image_path=image_path,
                ip_asset_id=ip_asset_id,
                **kwargs
            )
        )
        
        if result["status"] == "failed":
            error_msg = result.get("error", "Video generation failed")
            
            # Update task status to failed with error message
            update_task_status(
                self.request.id, 'failed', 0,
                completed_at=datetime.now(),
                error_message=error_msg
            )
            logger.error(f"Task {self.request.id} failed: {error_msg}")
            raise Exception(error_msg)
        
        # Update task status to completed
        execution_time = time.time() - start_time
        update_task_status(
            self.request.id, 'completed', 100,
            completed_at=datetime.now()
        )
        
        # Create content record with complete metadata
        execution_time = time.time() - start_time
        
        # Enrich result_data with additional metadata
        result_data = {
            **result,
            'ip_asset_id': ip_asset_id,
            'channel_id': kwargs.get('channel_id'),
        }
        
        create_content_record(
            task_id=self.request.id,
            task_type='video_generation',
            content_type='video',
            result_data=result_data,
            execution_time=execution_time
        )
        
        return {"status": "success", "data": result}
    
    except Exception as exc:
        # Only retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120)
        else:
            # Final retry failed, update task status
            error_msg = str(exc)
            update_task_status(
                self.request.id, 'failed', 0,
                completed_at=datetime.now(),
                error_message=error_msg
            )
            logger.error(f"Task {self.request.id} failed after {self.max_retries} retries: {error_msg}")
            # 必须 return，否则 Celery 认为任务成功
            return {"status": "failed", "error": error_msg}


@celery_app.task(bind=True, max_retries=0)
def train_lora_task(self, lora_id: int, training_params: dict) -> dict:
    """LoRA training task - supports both mock and real training modes."""
    from app.config.settings import settings
    
    # Check training mode from database settings (with .env fallback)
    training_mode = settings.get_lora_training_mode()
    
    if training_mode == "mock":
        return _mock_training(self, lora_id, training_params)
    else:
        return _real_training(self, lora_id, training_params)


def _mock_training(self, lora_id: int, training_params: dict) -> dict:
    """Mock LoRA training task - for workflow validation only."""
    import time
    import os
    from datetime import datetime
    from app.config.database import get_sync_session_safe
    from app.config.settings import settings
    from app.services.progress_reporter import progress_reporter
    from app.models.lora_model import LoRAModel
    from app.models.ip_asset import IPAsset
    from app.models.training_dataset import TrainingDataset
    from sqlalchemy import select, update
    
    try:
        now = datetime.now()
        # Use sync session with auto commit/rollback
        with get_sync_session_safe() as session:
            
            # Update status to training
            session.execute(
                update(LoRAModel)
                .where(LoRAModel.id == lora_id)
                .values(
                    status='training',
                    started_at=now,
                    progress=0
                )
            )
            
            # Mock training with progress updates
            total_epochs = training_params.get('epochs', 10)
            
            for epoch in range(1, total_epochs + 1):
                # Calculate progress
                progress = (epoch / total_epochs) * 100
                # Simulate loss decreasing
                current_loss = 0.15 - (epoch * 0.012)
                
                # ✅ Use ProgressReporter (updates DB + Redis asynchronously)
                progress_reporter.report(
                    lora_id=lora_id,
                    progress=progress,
                    epoch=epoch,
                    total_epochs=total_epochs,
                    loss=current_loss,
                    message=f"Mock training: Epoch {epoch}/{total_epochs}"
                )
                
                # Simulate training time (5 seconds per epoch)
                time.sleep(5)
            
            # ✅ Report completion
            progress_reporter.report(
                lora_id=lora_id,
                progress=100.0,
                epoch=total_epochs,
                total_epochs=total_epochs,
                loss=current_loss,
                message="Mock training completed"
            )
            
            # Generate mock LoRA model file
            mock_lora_dir = './data/lora_models'
            os.makedirs(mock_lora_dir, exist_ok=True)
            
            mock_lora_path = f"{mock_lora_dir}/mock_lora_{lora_id}_{int(time.time())}.safetensors"
            
            # Create placeholder file
            with open(mock_lora_path, 'w') as f:
                f.write(f"MOCK_LORA_MODEL\nlora_id: {lora_id}\ncreated: {now}\nepochs: {total_epochs}")
            
            # Update completion status
            completed_at = datetime.now()
            session.execute(
                update(LoRAModel)
                .where(LoRAModel.id == lora_id)
                .values(
                    status='completed',
                    progress=100,
                    current_epoch=total_epochs,
                    file_path=mock_lora_path,
                    final_loss=current_loss,
                    training_steps=total_epochs * 100,
                    training_time_minutes=total_epochs * 5 / 60,
                    completed_at=completed_at,
                    updated_at=completed_at
                )
            )
            
            # Update IP asset association after training completes
            try:
                # Get the dataset_id from lora_models
                lora_result = session.execute(
                    select(LoRAModel.dataset_id).where(LoRAModel.id == lora_id)
                )
                dataset_id = lora_result.scalar_one_or_none()
                
                if dataset_id:
                    # Get ip_asset_id from training_datasets
                    dataset_result = session.execute(
                        select(TrainingDataset.ip_asset_id).where(TrainingDataset.id == dataset_id)
                    )
                    ip_asset_id = dataset_result.scalar_one_or_none()
                    
                    if ip_asset_id:
                        # Update ip_assets.lora_model_id
                        session.execute(
                            update(IPAsset)
                            .where(IPAsset.id == ip_asset_id)
                            .values(
                                lora_model_id=lora_id,
                                updated_at=now
                            )
                        )
                        logger.info(f"Updated IP asset {ip_asset_id} with LoRA model {lora_id}")
            except Exception as e:
                logger.error(f"Failed to update IP association: {e}")
        
        # Auto-trigger quality assessment after training completes
        try:
            import asyncio
            from app.services.quality_assessor import QualityAssessor
            from app.models.lora_model import LoRAModel
            from app.config.database import get_db_session_standalone
            
            async def run_assessment():
                async with get_db_session_standalone() as db:
                    from sqlalchemy import select
                    result = await db.execute(select(LoRAModel).where(LoRAModel.id == lora_id))
                    lora_model = result.scalar_one_or_none()
                    if lora_model and lora_model.status == 'completed':
                        assessor = QualityAssessor()
                        await assessor.assess_model_quality(
                            lora_model=lora_model,
                            db=db,
                            num_test_images=5
                        )
            
            # Run assessment in background（使用当前事件循环）
            try:
                current_loop = asyncio.get_event_loop()
                current_loop.create_task(run_assessment())
            except RuntimeError:
                # 如果没有运行中的事件循环，同步执行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_assessment())
                loop.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Auto quality assessment failed: {e}")
        
        return {
            "status": "success",
            "model_path": mock_lora_path,
            "epochs": total_epochs,
            "final_loss": current_loss,
            "message": "Mock training completed (for workflow validation)"
        }
    
    except Exception as exc:
        # Update failed status
        try:
            update_task_status(
                self.request.id, 'failed',
                error_message=str(exc)
            )
        except Exception:
            pass
        
        raise Exception(f"Mock training failed: {str(exc)}")


def _real_training(self, lora_id: int, training_params: dict) -> dict:
    """Real LoRA training task with Kohya-ss."""
    import signal
    import subprocess
    from datetime import datetime
    from app.utils.time_utils import format_datetime_full
    from app.core.lora_trainer import lora_trainer
    from app.services.progress_reporter import progress_reporter
    from app.config.database import get_sync_session_safe
    from app.models.lora_model import LoRAModel
    from app.models.ip_asset import IPAsset
    from app.models.training_dataset import TrainingDataset
    from sqlalchemy import select, update
    
    # Track if training was cancelled
    training_cancelled = False
    
    def handle_revoke_signal(signum, frame):
        """Handle SIGTERM/SIGINT from Celery revoke"""
        nonlocal training_cancelled
        training_cancelled = True
        logger.warning(f"Received revoke signal for LoRA {lora_id}, cancelling training...")
        
        # Terminate the Kohya subprocess
        if lora_id in lora_trainer._active_processes:
            process = lora_trainer._active_processes[lora_id]
            try:
                logger.info(f"Terminating Kohya process {process.pid}")
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("Process didn't terminate gracefully, killing...")
                    process.kill()
                    process.wait(timeout=5)
                del lora_trainer._active_processes[lora_id]
                logger.info("✅ Kohya process terminated")
            except Exception as e:
                logger.error(f"Failed to terminate Kohya process: {e}")
    
    # Register signal handlers
    old_sigterm = signal.getsignal(signal.SIGTERM)
    old_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGTERM, handle_revoke_signal)
    signal.signal(signal.SIGINT, handle_revoke_signal)
    
    try:
        # Use sync session with auto commit/rollback
        with get_sync_session_safe() as session:
            now = datetime.now()
            
            # Update status to training
            session.execute(
                update(LoRAModel)
                .where(LoRAModel.id == lora_id)
                .values(
                    status='training',
                    started_at=now,
                    progress=0
                )
            )
        
        # ✅ Inject ProgressReporter into lora_trainer
        lora_trainer.set_progress_reporter(progress_reporter)
        
        # Run training
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                lora_trainer.start_training(lora_id)
            )
        finally:
            loop.close()
        
        # Check if training was cancelled
        if training_cancelled:
            logger.info(f"Training was cancelled for LoRA {lora_id}")
            # Restore original signal handlers
            signal.signal(signal.SIGTERM, old_sigterm)
            signal.signal(signal.SIGINT, old_sigint)
            raise Exception("Training was cancelled by user")
        
        # Update IP asset association after training completes
        try:
            with get_sync_session_safe() as session:
                # Get the dataset_id from lora_models
                lora_result = session.execute(
                    select(LoRAModel.dataset_id).where(LoRAModel.id == lora_id)
                )
                dataset_id = lora_result.scalar_one_or_none()
                
                if dataset_id:
                    # Get ip_asset_id from training_datasets
                    dataset_result = session.execute(
                        select(TrainingDataset.ip_asset_id).where(TrainingDataset.id == dataset_id)
                    )
                    ip_asset_id = dataset_result.scalar_one_or_none()
                    
                    if ip_asset_id:
                        # Update ip_assets.lora_model_id
                        session.execute(
                            update(IPAsset)
                            .where(IPAsset.id == ip_asset_id)
                            .values(
                                lora_model_id=lora_id,
                                updated_at=datetime.now()
                            )
                        )
                        logger.info(f"Updated IP asset {ip_asset_id} with LoRA model {lora_id}")
        except Exception as e:
            logger.error(f"Failed to update IP association: {e}")
        
        # Update to completed status
        update_task_status(self.request.id, 'completed', progress=100)
        logger.info(f"LoRA training completed: {lora_id}")
        
        return {"status": "success", "data": result}
    
    except Exception as exc:
        # Restore original signal handlers
        signal.signal(signal.SIGTERM, old_sigterm)
        signal.signal(signal.SIGINT, old_sigint)
        
        # Update failed status with error message
        error_msg = f"Real training failed: {str(exc)}"
        try:
            update_task_status(
                self.request.id, 'failed',
                error_message=error_msg
            )
        except Exception as db_exc:
            logger.error(f"Failed to update error in database: {db_exc}")
        
        raise Exception(error_msg)


@celery_app.task(bind=True)
def post_process_video_task(self, video_path: str, operations: list) -> dict:
    """Async video post-processing task."""
    try:
        import asyncio
        from app.core.post_processor import post_processor
        
        # 在Celery子线程中显式创建事件循环（避免'There is no current event loop'错误）
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 子线程中没有事件循环，需要创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            post_processor.process_video(video_path, operations)
        )
        
        return {"status": "success", "data": result}
    
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


@celery_app.task(bind=True, name='celery_worker.download_model_task', max_retries=2)
def download_model_task(self, model_id: str, mirror: str = "huggingface") -> dict:
    """
    Asynchronously download diffusion model.
    
    This task runs in the background and reports progress via Celery's update_state.
    Progress is estimated by monitoring the cache directory size growth.
    
    Args:
        model_id: Model identifier (stable_diffusion or ip_adapter)
        mirror: Download mirror (huggingface or modelscope)
    
    Returns:
        Download result dict
    """
    from app.services.model_downloader import model_downloader
    from pathlib import Path
    import threading
    import time
    
    logger.info(f"Starting model download task: {model_id} (mirror: {mirror})")
    
    model_config = model_downloader.MODELS.get(model_id, {})
    expected_size_mb = model_config.get("size_gb", 4.0) * 1024
    
    # huggingface_hub 缓存路径（优先使用项目配置）
    hf_cache = Path(settings.HF_HUB_CACHE_PATH).resolve()
    
    # 后台线程：监控缓存目录大小增长，定期报告进度
    stop_monitor = threading.Event()
    
    def _monitor_progress():
        """Background thread: poll cache dir size and call self.update_state()."""
        # 计算该模型相关目录的初始大小
        model_prefix = model_config.get("repo", "").replace("/", "--")
        
        # ✅ 修复：使用与 model_downloader 相同的路径逻辑
        from app.config.settings import settings
        
        # 优先检查自定义目录
        custom_models_dir = Path(settings.MODELS_PATH)
        custom_model_dir = custom_models_dir / f"models--{model_prefix}"
        
        if custom_model_dir.exists():
            model_cache_dir = custom_model_dir
        else:
            # fallback 到 huggingface 默认缓存
            hf_cache = Path(settings.HF_HUB_CACHE_PATH).resolve()
            model_cache_dir = hf_cache / f"models--{model_prefix}" if model_prefix else hf_cache
        
        start_size = 0
        start_time = time.time()
        last_size = 0
        
        if model_cache_dir.exists():
            try:
                start_size = sum(f.stat().st_size for f in model_cache_dir.rglob('*') if f.is_file()) / (1024 * 1024)
                last_size = start_size
            except Exception:
                pass
        
        last_reported = 0
        
        while not stop_monitor.is_set():
            try:
                current_size = 0
                if model_cache_dir.exists():
                    current_size = sum(f.stat().st_size for f in model_cache_dir.rglob('*') if f.is_file()) / (1024 * 1024)
                
                downloaded_mb = current_size - start_size
                elapsed = time.time() - start_time
                
                # ✅ 修复：即使目录不存在，也显示"准备中"状态
                if current_size == 0 and elapsed < 60:
                    progress = 0
                    status_msg = "Preparing download..."
                else:
                    progress = min(int((downloaded_mb / expected_size_mb) * 100), 99)  # cap at 99% until done
                    status_msg = "Downloading..."
                
                # ✅ 修复：计算实时速度
                speed_mbps = (current_size - last_size) / 10.0  # 10秒间隔
                
                # ✅ 修复：即使进度没变化也定期更新（证明任务活着）
                # 注意：在后台线程中调用self.update_state()需要确保self有效
                try:
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'progress': progress,
                            'downloaded_mb': round(downloaded_mb, 1),
                            'total_mb': round(expected_size_mb, 1),
                            'speed_mbps': round(speed_mbps, 1),
                            'eta_seconds': round((expected_size_mb - downloaded_mb) / max(0.1, speed_mbps), 0) if speed_mbps > 0.1 else 0,
                            'status_msg': status_msg
                        }
                    )
                except Exception as update_err:
                    logger.debug(f"Failed to update state: {update_err}")
                
                last_reported = progress
                last_size = current_size
                
            except Exception as e:
                logger.debug(f"Progress monitoring error: {e}")  # Ignore monitoring errors
            
            stop_monitor.wait(10)  # Poll every 10 seconds
    
    # 启动监控线程
    monitor_thread = threading.Thread(target=_monitor_progress, daemon=True)
    monitor_thread.start()
    
    try:
        # 执行下载（阻塞调用）
        result = model_downloader.download_model(
            model_id=model_id,
            mirror=mirror,
            progress_callback=None
        )
        
        # 停止监控并报告完成
        stop_monitor.set()
        monitor_thread.join(timeout=3)
        
        logger.info(f"Model download completed: {model_id}")
        
        return {
            "success": True,
            "model_id": model_id,
            "model_name": result["model_name"],
            "path": result["path"],
            "size_gb": result["size_gb"],
            "mirror": mirror
        }
        
    except Exception as exc:
        stop_monitor.set()  # 确保监控线程退出
        monitor_thread.join(timeout=3)
        logger.error(f"Model download failed: {model_id} - {exc}")
        return {
            "success": False,
            "model_id": model_id,
            "error": str(exc)
        }


# =============================================================================
# FlowPipe Workflow Execution Task
# =============================================================================

# Map node types to content_type for GeneratedContent records
_NODE_TYPE_TO_CONTENT = {
    "ImageSave": "image",
    "CloudImage": "image",
    "CloudVideo": "video",
    "LLMText": "story",
}


def _persist_workflow_outputs(task_id, workflow_name, primary_output, runtime_inputs, execution_time):
    """
    Create GeneratedContent and IPMultiView records from workflow execution outputs.
    
    This is the 'last mile' data persistence for FlowPipe workflows.
    """
    if not primary_output:
        logger.warning(f"Workflow {task_id}: no output nodes found, skipping persistence")
        return
    
    node_type = primary_output["node_type"]
    outputs = primary_output["outputs"]
    content_type = _NODE_TYPE_TO_CONTENT.get(node_type)
    
    if not content_type:
        logger.info(f"Workflow {task_id}: output node '{node_type}' has no content mapping, skipping")
        return
    
    # Extract file path based on node type
    file_path = ""
    if node_type == "ImageSave":
        file_path = outputs.get("path", "")
    elif node_type == "CloudImage":
        file_path = outputs.get("path", "") or outputs.get("url", "")
    elif node_type == "CloudVideo":
        file_path = outputs.get("video_path", "") or outputs.get("video_url", "")
    elif node_type == "LLMText":
        file_path = ""  # Text content stored inline
    
    ip_asset_id = runtime_inputs.get("ip_asset_id")
    view_type = runtime_inputs.get("view_type")
    
    # Build result_data for create_content_record
    text_content = outputs.get("text", "") if node_type == "LLMText" else ""
    result_data = {
        "title": f"{workflow_name} - {task_id[:8]}",
        "description": f"Workflow: {workflow_name}",
        "file_path": file_path,
        "output_path": file_path,
        "ip_asset_id": ip_asset_id,
        "content": text_content,
        "params": {
            "workflow_name": workflow_name,
            "node_type": node_type,
            "runtime_inputs": {k: str(v)[:200] for k, v in runtime_inputs.items()},
        },
    }
    
    try:
        create_content_record(
            task_id=task_id,
            task_type="workflow_execution",
            content_type=content_type,
            result_data=result_data,
            execution_time=execution_time,
        )
        logger.info(f"Workflow {task_id}: created {content_type} content record")
    except Exception as e:
        logger.error(f"Workflow {task_id}: failed to create content record: {e}", exc_info=True)
    
    # Create IPMultiView record for image outputs with ip_asset_id + view_type
    if content_type == "image" and file_path and ip_asset_id and view_type:
        try:
            from app.models.ip_multi_view import IPMultiView
            from app.config.database import get_sync_session_safe
            
            with get_sync_session_safe() as session:
                multi_view = IPMultiView(
                    ip_asset_id=ip_asset_id,
                    view_type=view_type,
                    image_path=file_path,
                    source="workflow",
                    generation_params={
                        "workflow_name": workflow_name,
                        "task_id": task_id,
                        "runtime_inputs": {k: str(v)[:200] for k, v in runtime_inputs.items()},
                        "generation_time": execution_time,
                    },
                    is_primary=(view_type == "front"),
                )
                session.add(multi_view)
                
            logger.info(f"Workflow {task_id}: created IPMultiView for IP {ip_asset_id}, view {view_type}")
        except Exception as e:
            logger.error(f"Workflow {task_id}: failed to create IPMultiView: {e}", exc_info=True)

@celery_app.task(bind=True, name="celery_worker.execute_workflow_task")
def execute_workflow_task(self, workflow_json: dict, runtime_inputs: dict = None) -> dict:
    """
    Execute a FlowPipe workflow asynchronously.
    
    Args:
        workflow_json: Complete workflow definition dict
        runtime_inputs: External inputs (e.g. image paths, IP asset data)
    
    Returns:
        Dict with execution results and output node data
    """
    import time
    import asyncio
    from datetime import datetime
    
    start_time = time.time()
    task_id = self.request.id
    
    try:
        update_task_status(task_id, 'running', 10, started_at=datetime.now())
        
        # Import FlowPipe engine - 必须在函数内强制添加项目根目录到 sys.path
        # （Celery 框架会在启动后重置 sys.path，模块级的 insert 会被覆盖）
        import sys as _sys
        from pathlib import Path as _Path
        _project_root = str(_Path(__file__).resolve().parent)
        if _project_root not in _sys.path:
            _sys.path.insert(0, _project_root)
        from flowpipe import WorkflowExecutor, dict_to_workflow
        from flowpipe.core.registry import NodeRegistry
        import flowpipe.nodes  # Ensure nodes are registered
        
        # Parse workflow
        workflow = dict_to_workflow(workflow_json)
        
        update_task_status(task_id, 'running', 30)
        
        # Execute
        executor = WorkflowExecutor(registry=NodeRegistry)
        
        # Run async executor in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    executor.execute(workflow, runtime_inputs)
                )
                node_outputs = future.result()
        else:
            node_outputs = loop.run_until_complete(
                executor.execute(workflow, runtime_inputs)
            )
        
        update_task_status(task_id, 'running', 90)
        
        # Collect output node results
        output_results = {}
        primary_output = None  # First output node for content record
        for node_id, outputs in node_outputs.items():
            if node_id.startswith("__"):
                continue
            try:
                node_instance = workflow.get_node(node_id)
                if node_instance:
                    node_cls = NodeRegistry.get(node_instance.type)
                    if node_cls.OUTPUT_NODE:
                        output_results[node_id] = {
                            "type": node_instance.type,
                            "outputs": {k: str(v)[:200] for k, v in outputs.items()},
                        }
                        if primary_output is None:
                            primary_output = {
                                "node_type": node_instance.type,
                                "outputs": outputs,
                            }
            except Exception:
                pass
        
        execution_time = time.time() - start_time
        
        # --- Data persistence: create GeneratedContent + IPMultiView records ---
        _persist_workflow_outputs(
            task_id=task_id,
            workflow_name=workflow.name,
            primary_output=primary_output,
            runtime_inputs=runtime_inputs or {},
            execution_time=execution_time,
        )
        
        update_task_status(
            task_id, 'completed', 100,
            completed_at=datetime.now()
        )
        
        return {
            "success": True,
            "workflow_name": workflow.name,
            "execution_time": execution_time,
            "node_count": len(workflow.nodes),
            "outputs": output_results,
        }
        
    except Exception as exc:
        execution_time = time.time() - start_time
        logger.error(f"Workflow execution failed: {exc}", exc_info=True)
        
        update_task_status(
            task_id, 'failed', 0,
            error_message=f"Workflow failed: {str(exc)}",
            completed_at=datetime.now()
        )
        
        return {
            "success": False,
            "error": str(exc),
            "execution_time": execution_time,
        }
