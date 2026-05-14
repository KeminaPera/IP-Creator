"""Celery Worker Configuration

Defines all asynchronous task definitions for background processing
including LLM calls, LoRA training, and video generation.
"""
import asyncio
from datetime import datetime
from celery import Celery
from celery.signals import worker_process_init, worker_ready
from app.config.settings import settings
from typing import Optional
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession

# Eager-import all ORM models so SQLAlchemy mappers can resolve string-based
# relationships (e.g. LoRAModel.quality_reports -> 'QualityReport') in workers.
from app.models import (  # noqa: F401
    user, ip_asset, llm_model, llm_provider, lora_model,
    task, generated_content, system_setting, quality_report,
)

# Task modules are defined directly in this file

# =============================================================================
# Celery 队列 SSOT (Single Source of Truth)
# -----------------------------------------------------------------------------
# CELERY_QUEUES: worker 必须监听的全部队列, 启动脚本通过 import 此常量派生 -Q 参数
#                (start_celery.sh / docker-compose.yml / start.bat 都读这里)
# TASK_ROUTES  : 任务名 -> 队列 的路由映射, 任何使用的 queue 必须出现在 CELERY_QUEUES 中
# 修改时务必两个变量同步, worker_ready 信号会在启动时做一致性校验.
# =============================================================================
CELERY_QUEUES = [
    "celery",              # 默认队列 (兼容未路由任务)
    "story_generation",    # 文本 / 剧本生成
    "image_generation",    # 图像生成
    "video_generation",    # 视频生成
    "training",            # LoRA / 微调训练
]

TASK_ROUTES = {
    "celery_worker.generate_image_task": {"queue": "image_generation"},
    "celery_worker.generate_story_task": {"queue": "story_generation"},
    "celery_worker.generate_video_task": {"queue": "video_generation"},
    "celery_worker.download_model_task": {"queue": "default"},  # 下载任务走默认队列
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
            print(
                f"[Celery Worker] ⚠️  WARNING: task_routes 路由到 {sorted(missing)} "
                f"但 worker 未监听这些队列！请检查启动命令的 -Q 参数。"
                f" (当前监听: {sorted(listening)})"
            )
        else:
            print(
                f"[Celery Worker] ✅ 队列一致性校验通过，监听 {sorted(listening)}"
            )
    except Exception as e:
        print(f"[Celery Worker] 队列一致性校验异常: {e}")


@worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize worker process: event loop + LLM manager."""
    try:
        # 创建全局事件循环（所有任务复用）
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        from app.core.llm_manager import llm_manager
        loop.run_until_complete(llm_manager.initialize_models())
        print(f"[Celery Worker] LLM manager initialized, active model: {llm_manager.registry.get_active_model_id()}")
    except Exception as e:
        print(f"[Celery Worker] Failed to initialize LLM manager: {e}")


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
        import sqlite3
        import json
        from datetime import datetime
        from pathlib import Path
        
        db_path = './data/ip_creator.db'
        
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
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO generated_contents (
                task_id, task_type, content_type, title, description,
                file_path, thumbnail_path, file_size,
                duration_seconds, resolution, word_count,
                ip_asset_id, parameters, content_metadata,
                status, execution_time_seconds, channel_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """, (
            task_id, task_type, content_type, title, description,
            file_path, thumbnail_path, file_size,
            duration_seconds, resolution, word_count,
            ip_asset_id, json.dumps(parameters) if parameters else None,
            json.dumps(content_metadata),
            'completed', execution_time, channel_id
        ))
        
        conn.commit()
        conn.close()
        
        from app.utils.logger import logger
        logger.info(f"Created content record: {content_type} - {title} (ID: {task_id})")
        
    except Exception as e:
        from app.utils.logger import logger
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
        from app.utils.logger import logger
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
            from app.utils.logger import logger
            logger.error(f"FFmpeg failed: {result.stderr}")
            return None
    except FileNotFoundError:
        from app.utils.logger import logger
        logger.warning("FFmpeg not installed, skipping video thumbnail generation")
        return None
    except Exception as e:
        from app.utils.logger import logger
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
        import sqlite3
        
        # Update task status to running and set started_at using local time
        db_path = './data/ip_creator.db'
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE task_records SET status='running', started_at=?, progress=10 WHERE task_id=?",
            (now, self.request.id)
        )
        conn.commit()
        conn.close()
        
        # 复用 worker_process_init 中创建的全局事件循环
        loop = asyncio.get_event_loop()
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
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE task_records SET status='failed', progress=0 WHERE task_id=?",
                (self.request.id,)
            )
            conn.commit()
            conn.close()
            raise Exception(result.get("error", "Story generation failed"))
        
        # Update task status to completed and set completed_at
        completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE task_records SET status='completed', completed_at=?, progress=100 WHERE task_id=?",
            (completed_at, self.request.id)
        )
        conn.commit()
        conn.close()
        
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
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE task_records SET status='failed', progress=0 WHERE task_id=?",
                (self.request.id,)
            )
            conn.commit()
            conn.close()
        except:
            pass
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=2)
def generate_image_task(self, prompt: str, ip_asset_id: int = 0, **kwargs) -> dict:
    """Async image generation task with Diffusers."""
    import time
    from datetime import datetime
    import sqlite3
    start_time = time.time()
    db_path = './data/ip_creator.db'
    
    try:
        import asyncio
        from app.core.video_generator import video_generator
        
        # Update task status to running
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE task_records SET status='running', started_at=?, progress=10 WHERE task_id=?",
            (now, self.request.id)
        )
        conn.commit()
        conn.close()
        
        # 复用全局事件循环
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            video_generator.generate_image(
                prompt=prompt,
                ip_asset_id=ip_asset_id,
                **kwargs
            )
        )
        
        if result["status"] == "failed":
            error_msg = result.get("error", "Image generation failed")
            
            # Update task status to failed with error message
            completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE task_records 
                   SET status='failed', 
                       error_message=?, 
                       progress=0, 
                       completed_at=?
                   WHERE task_id=?""",
                (error_msg, completed_at, self.request.id)
            )
            conn.commit()
            conn.close()
            
            from app.utils.logger import logger
            logger.error(f"Task {self.request.id} failed: {error_msg}")
            raise Exception(error_msg)
        
        # Update task status to completed
        execution_time = time.time() - start_time
        completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE task_records 
               SET status='completed', 
                   progress=100, 
                   completed_at=?,
                   execution_time_seconds=?
               WHERE task_id=?""",
            (completed_at, execution_time, self.request.id)
        )
        conn.commit()
        conn.close()
        
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
        
        return {"status": "success", "data": result}
    
    except Exception as exc:
        # Only retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120)
        else:
            # Final retry failed, update task status
            error_msg = str(exc)
            completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE task_records 
                   SET status='failed', 
                       error_message=?, 
                       progress=0, 
                       completed_at=?
                   WHERE task_id=?""",
                (error_msg, completed_at, self.request.id)
            )
            conn.commit()
            conn.close()
            
            from app.utils.logger import logger
            logger.error(f"Task {self.request.id} permanently failed after {self.max_retries} retries: {error_msg}")
            return {"status": "failed", "error": error_msg}


@celery_app.task(bind=True, max_retries=1)
def generate_video_task(self, prompt: str, image_path: str, ip_asset_id: int = 0, **kwargs) -> dict:
    """Async video generation task with Diffusers."""
    import time
    from datetime import datetime
    import sqlite3
    
    start_time = time.time()
    db_path = './data/ip_creator.db'
    
    try:
        import asyncio
        from app.core.video_generator import video_generator
        
        # Update task status to running
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE task_records SET status='running', started_at=?, progress=10 WHERE task_id=?",
            (now, self.request.id)
        )
        conn.commit()
        conn.close()
        
        # 复用全局事件循环
        loop = asyncio.get_event_loop()
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
            completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE task_records 
                   SET status='failed', 
                       error_message=?, 
                       progress=0, 
                       completed_at=?
                   WHERE task_id=?""",
                (error_msg, completed_at, self.request.id)
            )
            conn.commit()
            conn.close()
            
            from app.utils.logger import logger
            logger.error(f"Task {self.request.id} failed: {error_msg}")
            raise Exception(error_msg)
        
        # Update task status to completed
        execution_time = time.time() - start_time
        completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE task_records 
               SET status='completed', 
                   progress=100, 
                   completed_at=?,
                   execution_time_seconds=?
               WHERE task_id=?""",
            (completed_at, execution_time, self.request.id)
        )
        conn.commit()
        conn.close()
        
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
            completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE task_records 
                   SET status='failed', 
                       error_message=?, 
                       progress=0, 
                       completed_at=?
                   WHERE task_id=?""",
                (error_msg, completed_at, self.request.id)
            )
            conn.commit()
            conn.close()
            
            from app.utils.logger import logger
            logger.error(f"Task {self.request.id} failed after {self.max_retries} retries: {error_msg}")
            # 必须 return，否则 Celery 认为任务成功
            return {"status": "failed", "error": error_msg}


@celery_app.task(bind=True, max_retries=0)
def train_lora_task(self, lora_id: int, training_params: dict) -> dict:
    """LoRA training task - supports both mock and real training modes."""
    from app.config.settings import settings
    
    # Check training mode
    if settings.LORA_TRAINING_MODE == "mock":
        return _mock_training(self, lora_id, training_params)
    else:
        return _real_training(self, lora_id, training_params)


def _mock_training(self, lora_id: int, training_params: dict) -> dict:
    """Mock LoRA training task - for workflow validation only."""
    import sqlite3
    import time
    import os
    from datetime import datetime
    
    db_path = './data/ip_creator.db'
    
    try:
        # Update status to training
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute(
            "UPDATE lora_models SET status='training', started_at=?, progress=0 WHERE id=?",
            (now, lora_id)
        )
        conn.commit()
        
        # Mock training with progress updates
        total_epochs = training_params.get('epochs', 10)
        
        for epoch in range(1, total_epochs + 1):
            # Calculate progress
            progress = (epoch / total_epochs) * 100
            # Simulate loss decreasing
            current_loss = 0.15 - (epoch * 0.012)
            
            # Update progress in database
            cursor.execute(
                """UPDATE lora_models 
                   SET progress=?, 
                       current_loss=?,
                       current_epoch=?,
                       updated_at=?
                   WHERE id=?""",
                (progress, current_loss, epoch, now, lora_id)
            )
            conn.commit()
            
            # Simulate training time (5 seconds per epoch)
            time.sleep(5)
        
        # Generate mock LoRA model file
        mock_lora_dir = './data/lora_models'
        os.makedirs(mock_lora_dir, exist_ok=True)
        
        mock_lora_path = f"{mock_lora_dir}/mock_lora_{lora_id}_{int(time.time())}.safetensors"
        
        # Create placeholder file
        with open(mock_lora_path, 'w') as f:
            f.write(f"MOCK_LORA_MODEL\nlora_id: {lora_id}\ncreated: {now}\nepochs: {total_epochs}")
        
        # Update completion status
        completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            """UPDATE lora_models 
               SET status='completed',
                   progress=100,
                   current_epoch=?,
                   file_path=?,
                   final_loss=?,
                   training_steps=?,
                   training_time_minutes=?,
                   completed_at=?,
                   updated_at=?
               WHERE id=?""",
            (total_epochs, mock_lora_path, current_loss, total_epochs * 100, 
             total_epochs * 5 / 60, completed_at, completed_at, lora_id)
        )
        conn.commit()
        conn.close()
        
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
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE lora_models SET status='failed', error_message=? WHERE id=?",
                (str(exc), lora_id)
            )
            conn.commit()
            conn.close()
        except:
            pass
        
        raise Exception(f"Mock training failed: {str(exc)}")


def _real_training(self, lora_id: int, training_params: dict) -> dict:
    """Real LoRA training task with Kohya-sd (to be implemented when GPU is available)."""
    try:
        from app.core.lora_trainer import lora_trainer
        
        # 复用全局事件循环
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            lora_trainer.start_training(lora_id)
        )
        
        return {"status": "success", "data": result}
    
    except Exception as exc:
        raise Exception(f"Real training failed: {str(exc)}")


@celery_app.task(bind=True)
def post_process_video_task(self, video_path: str, operations: list) -> dict:
    """Async video post-processing task."""
    try:
        from app.core.post_processor import post_processor
        
        # 复用全局事件循环
        loop = asyncio.get_event_loop()
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
    from app.utils.logger import logger
    from pathlib import Path
    import threading
    import time
    
    logger.info(f"Starting model download task: {model_id} (mirror: {mirror})")
    
    model_config = model_downloader.MODELS.get(model_id, {})
    expected_size_mb = model_config.get("size_gb", 4.0) * 1024
    
    # huggingface_hub 实际缓存路径: ~/.cache/huggingface/hub/
    # cache_dir 参数指定的目录会包含 models--{repo} 子目录
    import os
    hf_cache = Path(os.path.expanduser("~/.cache/huggingface/hub"))
    
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
            hf_cache = Path(os.path.expanduser("~/.cache/huggingface/hub"))
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
