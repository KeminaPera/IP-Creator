"""
WebSocket全局实例

提供全局的WebSocket管理器和Redis监听器实例
"""
from app.websocket import ConnectionManager, RedisProgressListener

# Global WebSocket manager and Redis listener
ws_manager = ConnectionManager()
redis_listener = RedisProgressListener(ws_manager)

__all__ = ["ws_manager", "redis_listener"]
