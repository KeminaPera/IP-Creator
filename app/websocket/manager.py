"""
WebSocket连接管理器

管理所有活跃的WebSocket连接，按lora_id分组，支持广播消息
"""
from typing import Dict, List
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # {lora_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, lora_id: int):
        """接受WebSocket连接"""
        await websocket.accept()
        
        if lora_id not in self.active_connections:
            self.active_connections[lora_id] = []
        
        self.active_connections[lora_id].append(websocket)
        logger.info(f"✅ WebSocket connected for LoRA {lora_id} (total: {len(self.active_connections[lora_id])})")
    
    def disconnect(self, websocket: WebSocket, lora_id: int):
        """断开WebSocket连接"""
        if lora_id in self.active_connections:
            if websocket in self.active_connections[lora_id]:
                self.active_connections[lora_id].remove(websocket)
                logger.info(f"❌ WebSocket disconnected for LoRA {lora_id}")
            
            # 清理空列表
            if not self.active_connections[lora_id]:
                del self.active_connections[lora_id]
                logger.info(f"🗑️  No more connections for LoRA {lora_id}")
    
    async def send_progress(self, lora_id: int, data: dict):
        """向指定LoRA的所有连接发送进度消息"""
        message = json.dumps({
            "type": "progress_update",
            "data": data
        })
        
        await self._send_to_lora(lora_id, message)
    
    async def send_training_complete(self, lora_id: int, data: dict):
        """发送训练完成消息"""
        message = json.dumps({
            "type": "training_complete",
            "data": data
        })
        
        await self._send_to_lora(lora_id, message)
    
    async def send_training_failed(self, lora_id: int, error: str):
        """发送训练失败消息"""
        message = json.dumps({
            "type": "training_failed",
            "data": {"error": error}
        })
        
        await self._send_to_lora(lora_id, message)
    
    async def _send_to_lora(self, lora_id: int, message: str):
        """内部方法：发送消息到指定LoRA的所有连接"""
        if lora_id not in self.active_connections:
            return
        
        disconnected = []
        
        for connection in self.active_connections[lora_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn, lora_id)
    
    def get_connection_count(self, lora_id: int) -> int:
        """获取指定LoRA的连接数"""
        if lora_id not in self.active_connections:
            return 0
        return len(self.active_connections[lora_id])
