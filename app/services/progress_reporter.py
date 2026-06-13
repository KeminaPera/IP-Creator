"""
训练进度报告器

统一的进度报告入口，负责：
1. 更新数据库进度
2. 发布Redis进度（用于WebSocket推送）
3. 记录训练日志

设计原则：
- 异步非阻塞：不阻塞训练流程
- 容错处理：单个操作失败不影响其他操作
- 统一接口：Mock和Real模式使用相同的API
"""
import asyncio
import json
import time
import logging
from typing import Optional
from datetime import datetime

import redis
from sqlalchemy import update

from app.config.settings import settings
from app.config.database import get_db_session_standalone
from app.models.lora_model import LoRAModel
from app.services.training_logger import training_logger

logger = logging.getLogger(__name__)


class ProgressReporter:
    """训练进度报告器"""
    
    def __init__(self):
        """初始化Redis客户端"""
        redis_url = settings.REDIS_URL.rsplit('/', 1)[0] + '/3'
        self.redis_client = redis.from_url(
            redis_url, 
            decode_responses=True
        )
    
    async def report(
        self,
        lora_id: int,
        progress: float,
        epoch: int = 0,
        total_epochs: int = 0,
        loss: Optional[float] = None,
        message: Optional[str] = None
    ):
        """
        报告训练进度（统一入口）
        
        Args:
            lora_id: LoRA模型ID
            progress: 进度百分比 (0-100)
            epoch: 当前轮数
            total_epochs: 总轮数
            loss: 当前loss值
            message: 附加消息
        """
        # 直接await，确保进度更新完成
        # 在Celery环境中，create_task会被loop.close()取消
        await self._report_async(
            lora_id=lora_id,
            progress=progress,
            epoch=epoch,
            total_epochs=total_epochs,
            loss=loss,
            message=message
        )
    
    async def _report_async(
        self,
        lora_id: int,
        progress: float,
        epoch: int,
        total_epochs: int,
        loss: Optional[float],
        message: Optional[str]
    ):
        """异步执行所有报告操作"""
        
        # 1. 更新数据库（异步）
        try:
            await self._update_database(
                lora_id, progress, epoch, loss
            )
        except Exception as e:
            logger.error(f"Failed to update database: {e}")
        
        # 2. 发布Redis（异步）
        try:
            await self._publish_redis(
                lora_id, progress, epoch, loss
            )
        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}")
        
        # 3. 记录日志（同步，轻量）
        try:
            if message:
                await training_logger.log(
                    lora_id, message, level="PROGRESS"
                )
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
    
    async def _update_database(
        self,
        lora_id: int,
        progress: float,
        epoch: int,
        loss: Optional[float]
    ):
        """更新数据库进度"""
        async with get_db_session_standalone() as session:
            stmt = (
                update(LoRAModel)
                .where(LoRAModel.id == lora_id)
                .values(
                    progress=progress,
                    current_epoch=epoch,
                    current_loss=loss,
                    updated_at=datetime.now()
                )
            )
            await session.execute(stmt)
            await session.commit()
            logger.debug(f"✅ Database updated: LoRA {lora_id} - {progress:.1f}%")
    
    async def _publish_redis(
        self,
        lora_id: int,
        progress: float,
        epoch: int,
        loss: Optional[float]
    ):
        """发布进度到Redis"""
        data = {
            'progress': progress,
            'current_epoch': epoch,
            'current_loss': loss,
            'timestamp': time.time()
        }
        
        self.redis_client.publish(
            f'training_progress:{lora_id}',
            json.dumps(data)
        )
        logger.debug(f"📡 Redis published: LoRA {lora_id} - {progress:.1f}%")


# 全局单例
progress_reporter = ProgressReporter()
