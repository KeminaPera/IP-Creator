"""
Task Record Model

Tracks all asynchronous tasks including LoRA training,
image generation, video generation, and post-processing.
"""
from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.config.database import Base


class TaskRecord(Base):
    """
    Asynchronous task tracking and audit trail.
    
    Records all background tasks with status, progress, parameters,
    and results for monitoring and historical reference.
    """
    __tablename__ = "task_records"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Task Identification
    task_id = Column(String(100), nullable=False, unique=True, index=True, comment="Celery task ID")
    task_type = Column(String(50), nullable=False, index=True, comment="lora_training, image_gen, video_gen, post_process")
    
    # IP Association
    ip_asset_id = Column(Integer, ForeignKey("ip_assets.id"), nullable=True, index=True, comment="Associated IP asset ID")
    
    # Task Status
    status = Column(String(20), default="pending", index=True, comment="pending, running, completed, failed, cancelled")
    progress = Column(Float, default=0.0, comment="Progress percentage (0-100)")
    
    # Task Configuration
    parameters = Column(JSON, nullable=True, comment="Task input parameters")
    priority = Column(Integer, default=0, comment="Task priority (higher = more important)")
    channel_id = Column(Integer, nullable=True, comment="LLM channel ID used for this task")
    
    # Results
    result_path = Column(String(500), nullable=True, comment="Path to generated output")
    result_metadata = Column(JSON, nullable=True, comment="Additional result information")
    
    # Error Handling
    error_message = Column(Text, nullable=True, comment="Error details if failed")
    retry_count = Column(Integer, default=0, comment="Number of retry attempts")
    
    # Resource Tracking
    gpu_memory_used = Column(Float, nullable=True, comment="GPU memory used in GB")
    execution_time_seconds = Column(Float, nullable=True, comment="Total execution time")
    
    # Metadata
    created_by = Column(Integer, nullable=True, comment="User ID who created the task")
    created_at = Column(DateTime, server_default=func.now(), index=True, comment="Creation timestamp")
    started_at = Column(DateTime, nullable=True, index=True, comment="Task start time")
    completed_at = Column(DateTime, nullable=True, index=True, comment="Task completion time")
    
    # Composite Indexes for common query patterns
    __table_args__ = (
        # Task monitor list: filter by IP, status, order by time
        Index('idx_task_ip_status_created', 'ip_asset_id', 'status', 'created_at'),
        # Task status monitor: filter by status, order by time
        Index('idx_task_status_created', 'status', 'created_at'),
        # Channel task query: filter by channel, status
        Index('idx_task_channel_status', 'channel_id', 'status'),
    )
    
    def __repr__(self):
        return f"<TaskRecord(id={self.id}, type={self.task_type}, status={self.status})>"
