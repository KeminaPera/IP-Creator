"""
Training WebSocket handlers for real-time log streaming.

Provides WebSocket endpoints for clients to receive real-time training logs.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict

from app.services.training_logger import training_logger
from app.websocket.instances import ws_manager

router = APIRouter()

# Track active connections
active_connections: Dict[int, list] = {}


@router.websocket("/ws/training/{lora_id}")
async def training_websocket(websocket: WebSocket, lora_id: int):
    """
    WebSocket endpoint for real-time training log streaming.
    
    Args:
        websocket: WebSocket connection
        lora_id: LoRA model ID to monitor
    
    Usage:
        const ws = new WebSocket('ws://localhost:8000/ws/training/123')
        ws.onmessage = (event) => {
            const log = JSON.parse(event.data)
            console.log(log)
        }
    """
    # Connect to the WebSocket using ConnectionManager
    await ws_manager.connect(websocket, lora_id)
    
    # Send historical logs immediately
    recent_logs = await training_logger.get_logs(lora_id, limit=50)
    for log in recent_logs:
        await websocket.send_json(log)
    
    try:
        # Keep connection alive and handle client messages
        while True:
            # Wait for messages from client (optional)
            data = await websocket.receive_text()
            
            # Handle client commands
            if data == "ping":
                await websocket.send_json({"type": "pong"})
            elif data == "get_metrics":
                metrics = await training_logger.get_metrics(lora_id)
                await websocket.send_json({
                    "type": "metrics",
                    "data": metrics
                })
    
    except WebSocketDisconnect:
        # Client disconnected
        ws_manager.disconnect(websocket, lora_id)
    except Exception as e:
        # Handle other errors
        ws_manager.disconnect(websocket, lora_id)
        raise


@router.websocket("/ws/training/{lora_id}/logs")
async def training_logs_websocket(websocket: WebSocket, lora_id: int):
    """
    WebSocket endpoint for training logs only (no metrics).
    
    This is a lighter version that only sends log messages.
    
    Args:
        websocket: WebSocket connection
        lora_id: LoRA model ID to monitor
    """
    await websocket.accept()
    await training_logger.register_websocket(lora_id, websocket)
    
    try:
        while True:
            # Just keep connection alive
            await websocket.receive_text()
    
    except WebSocketDisconnect:
        await training_logger.unregister_websocket(lora_id, websocket)
    except Exception as e:
        await training_logger.unregister_websocket(lora_id, websocket)
        raise
