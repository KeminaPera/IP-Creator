"""
WebSocket路由

提供训练进度实时推送的WebSocket端点
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import logging

from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter()

# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/ws/training/{lora_id}")
async def training_websocket(websocket: WebSocket, lora_id: int):
    """
    WebSocket端点：实时推送训练进度
    
    连接示例:
    ws://localhost:8000/api/v1/ws/training/2
    
    消息格式:
    - 服务端推送: {"type": "progress_update", "data": {...}}
    - 客户端发送: {"action": "cancel"}  # 取消训练
    """
    await manager.connect(websocket, lora_id)
    
    try:
        # 保持连接，接收前端消息
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理前端发送的指令
            action = message.get("action")
            
            if action == "cancel":
                # 取消训练
                logger.info(f"🛑 Cancel training request for LoRA {lora_id}")
                
                from celery_worker import train_lora_task
                from app.config.database import async_session_factory
                from app.models.lora_model import LoRAModel
                from sqlalchemy import select
                
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(LoRAModel).where(LoRAModel.id == lora_id)
                    )
                    lora_model = result.scalar_one_or_none()
                    
                    if lora_model and lora_model.celery_task_id:
                        # Revoke Celery任务
                        task_result = train_lora_task.AsyncResult(lora_model.celery_task_id)
                        task_result.revoke(terminate=True, signal="SIGTERM")
                        
                        # 更新数据库状态
                        lora_model.status = "cancelled"
                        await session.commit()
                        
                        # 发送取消成功消息
                        await manager.send_training_complete(
                            lora_id,
                            {"message": "Training cancelled by user"}
                        )
                        
                        logger.info(f"✅ Training cancelled for LoRA {lora_id}")
                    else:
                        logger.warning(f"No celery task found for LoRA {lora_id}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for LoRA {lora_id}")
        manager.disconnect(websocket, lora_id)
    except Exception as e:
        logger.error(f"WebSocket error for LoRA {lora_id}: {e}")
        manager.disconnect(websocket, lora_id)
