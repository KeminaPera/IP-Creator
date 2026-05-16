"""
Redis Pub/Sub监听器

监听Redis中的训练进度消息，并转发到WebSocket连接
"""
import asyncio
import json
import logging
from typing import Optional
import redis.asyncio as redis
from app.config.settings import settings
from .manager import ConnectionManager

logger = logging.getLogger(__name__)


class RedisProgressListener:
    """Redis进度监听器"""
    
    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        # Use settings config, change db from 0 to 3 for WebSocket progress
        redis_url = settings.REDIS_URL.rsplit('/', 1)[0] + '/3'
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动监听器"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding="utf-8"
            )
            
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("training_progress:*")
            
            # 启动监听任务
            self.task = asyncio.create_task(self._listen())
            logger.info("✅ Redis progress listener started")
        except Exception as e:
            logger.error(f"Failed to start Redis listener: {e}")
            raise
    
    async def stop(self):
        """停止监听器"""
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            try:
                await self.pubsub.unsubscribe()
                await self.pubsub.close()
            except:
                pass
        
        if self.redis_client:
            try:
                await self.redis_client.close()
            except:
                pass
        
        logger.info("🛑 Redis progress listener stopped")
    
    async def _listen(self):
        """监听Redis消息并转发到WebSocket"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self._handle_message(message)
        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
            raise
    
    async def _handle_message(self, message: dict):
        """处理Redis消息"""
        try:
            channel = message["channel"]
                
            # Validate channel format
            if not channel.startswith("training_progress:"):
                logger.warning(f"Invalid channel format: {channel}")
                return
                
            data = json.loads(message["data"])
                
            # Extract lora_id from channel
            # Channel format: training_progress:2
            lora_id_str = channel.split(":")[-1]
            try:
                lora_id = int(lora_id_str)
            except ValueError:
                logger.error(f"Invalid lora_id in channel: {channel}")
                return
                
            # Forward to WebSocket
            await self.manager.send_progress(lora_id, data)
                
            logger.debug(f"📡 Forwarded progress for LoRA {lora_id}: {data.get('progress', 0):.1f}%")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Redis message: {e}")
        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")
