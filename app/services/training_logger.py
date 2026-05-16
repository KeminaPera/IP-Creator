"""
Training Logger Service

Provides real-time training log management, WebSocket streaming,
and log file handling for LoRA training processes.
"""
import asyncio
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import deque
from app.config.settings import settings
from app.utils.logger import logger


class TrainingLogEntry:
    """Single training log entry."""
    
    def __init__(
        self,
        timestamp: datetime,
        level: str,
        message: str,
        epoch: Optional[int] = None,
        loss: Optional[float] = None,
        lr: Optional[float] = None,
    ):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.epoch = epoch
        self.loss = loss
        self.lr = lr
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "epoch": self.epoch,
            "loss": self.loss,
            "lr": self.lr,
        }


class TrainingLogger:
    """
    Service for managing training logs.
    
    Features:
    - Real-time log streaming via WebSocket
    - Log file persistence
    - Training metrics tracking
    """
    
    def __init__(self):
        """Initialize training logger."""
        # Use STORAGE_PATH for logs
        self.log_dir = Path(settings.STORAGE_PATH) / "logs" / "training"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory log buffers (recent logs)
        self.log_buffers: Dict[int, deque] = {}
        self.max_buffer_size = 1000
        
        # WebSocket connections
        self.ws_connections: Dict[int, List] = {}
    
    def get_log_file(self, lora_id: int) -> Path:
        """Get log file path for a training task."""
        return self.log_dir / f"lora_{lora_id}.log"
    
    async def log(
        self,
        lora_id: int,
        message: str,
        level: str = "INFO",
        epoch: Optional[int] = None,
        loss: Optional[float] = None,
        lr: Optional[float] = None,
    ):
        """
        Add a log entry.
        
        Args:
            lora_id: LoRA training task ID
            message: Log message
            level: Log level (INFO, WARNING, ERROR)
            epoch: Current epoch number
            loss: Current loss value
            lr: Current learning rate
        """
        entry = TrainingLogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            epoch=epoch,
            loss=loss,
            lr=lr,
        )
        
        # Add to in-memory buffer
        if lora_id not in self.log_buffers:
            self.log_buffers[lora_id] = deque(maxlen=self.max_buffer_size)
        self.log_buffers[lora_id].append(entry)
        
        # Write to file
        log_file = self.get_log_file(lora_id)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")
        
        # Broadcast to WebSocket connections
        if lora_id in self.ws_connections:
            message_data = entry.to_dict()
            disconnected = []
            
            for ws in self.ws_connections[lora_id]:
                try:
                    await ws.send_text(json.dumps(message_data))
                except Exception as e:
                    logger.error(f"WebSocket send error: {e}")
                    disconnected.append(ws)
            
            # Remove disconnected clients
            for ws in disconnected:
                self.ws_connections[lora_id].remove(ws)
    
    async def get_logs(
        self,
        lora_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get training logs.
        
        Args:
            lora_id: LoRA training task ID
            limit: Maximum number of logs to return
            offset: Offset from most recent
            
        Returns:
            List of log entries
            
        Priority:
        1. Memory buffer (fast, recent logs)
        2. Log file (persistent, historical logs)
        """
        logs = []
        
        # 1. Try to get from memory buffer first (fast)
        if lora_id in self.log_buffers:
            buffer_logs = list(self.log_buffers[lora_id])
            logs = buffer_logs[-(offset + limit):len(buffer_logs) - offset if offset > 0 else None]
        
        # 2. If memory is empty, load from file (persistent)
        if not logs:
            log_file = self.get_log_file(lora_id)
            if log_file.exists():
                logs = self._load_logs_from_file(log_file, limit, offset)
        
        # Convert to dict format
        return [
            log.to_dict() if hasattr(log, 'to_dict') else log
            for log in logs
        ]
    
    def _load_logs_from_file(
        self,
        log_file: Path,
        limit: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """
        Load logs from file.
        
        Args:
            log_file: Path to log file
            limit: Maximum number of logs to return
            offset: Offset from most recent
            
        Returns:
            List of log entries
        """
        try:
            all_logs = []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            log_data = json.loads(line)
                            all_logs.append(log_data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid log line in {log_file}: {line[:50]}")
                            continue
            
            # Apply offset and limit
            return all_logs[-(offset + limit):len(all_logs) - offset if offset > 0 else None]
        
        except Exception as e:
            logger.error(f"Failed to load logs from file {log_file}: {e}")
            return []
    
    async def get_metrics(self, lora_id: int) -> Dict[str, Any]:
        """
        Extract training metrics from logs.
        
        Args:
            lora_id: LoRA training task ID
            
        Returns:
            Training metrics (loss curve, epochs, etc.)
        """
        if lora_id not in self.log_buffers:
            return {"epochs": [], "losses": [], "learning_rates": []}
        
        epochs = []
        losses = []
        learning_rates = []
        
        for entry in self.log_buffers[lora_id]:
            if entry.epoch is not None:
                epochs.append(entry.epoch)
            if entry.loss is not None:
                losses.append(entry.loss)
            if entry.lr is not None:
                learning_rates.append(entry.lr)
        
        return {
            "epochs": epochs,
            "losses": losses,
            "learning_rates": learning_rates,
            "current_epoch": epochs[-1] if epochs else 0,
            "current_loss": losses[-1] if losses else None,
            "current_lr": learning_rates[-1] if learning_rates else None,
        }
    
    async def register_websocket(self, lora_id: int, websocket):
        """
        Register a WebSocket connection for real-time logs.
        
        Args:
            lora_id: LoRA training task ID
            websocket: WebSocket connection
        """
        if lora_id not in self.ws_connections:
            self.ws_connections[lora_id] = []
        
        self.ws_connections[lora_id].append(websocket)
        logger.info(f"WebSocket registered for training {lora_id}")
    
    async def unregister_websocket(self, lora_id: int, websocket):
        """
        Unregister a WebSocket connection.
        
        Args:
            lora_id: LoRA training task ID
            websocket: WebSocket connection
        """
        if lora_id in self.ws_connections:
            try:
                self.ws_connections[lora_id].remove(websocket)
                logger.info(f"WebSocket unregistered for training {lora_id}")
            except ValueError:
                pass
    
    def clear_logs(self, lora_id: int):
        """
        Clear logs for a training task.
        
        Args:
            lora_id: LoRA training task ID
        """
        if lora_id in self.log_buffers:
            self.log_buffers[lora_id].clear()
        
        # Delete log file
        log_file = self.get_log_file(lora_id)
        if log_file.exists():
            log_file.unlink()


# Global training logger instance
training_logger = TrainingLogger()
