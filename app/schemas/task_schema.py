"""
Task Record Schemas

Pydantic schemas for asynchronous task tracking, monitoring,
and management with progress and status information.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TaskType(str, Enum):
    """Task type enumeration."""
    LORA_TRAINING = "lora_training"
    IMAGE_GENERATION = "image_gen"
    VIDEO_GENERATION = "video_gen"
    POST_PROCESSING = "post_process"
    STORY_GENERATION = "story_gen"


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRecordBase(BaseModel):
    """Base schema for task record."""
    task_type: TaskType = Field(..., description="Type of task")
    priority: int = Field(0, ge=0, le=10, description="Task priority")


class TaskRecordCreate(TaskRecordBase):
    """Schema for creating a new task record."""
    task_id: str = Field(..., description="Celery task ID")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Task parameters")
    created_by: Optional[int] = Field(None, description="User ID")
    ip_asset_id: Optional[int] = Field(None, description="Associated IP asset ID")


class TaskRecordUpdate(BaseModel):
    """Schema for updating task status and progress."""
    status: Optional[TaskStatus] = None
    progress: Optional[float] = Field(None, ge=0.0, le=100.0)
    result_path: Optional[str] = Field(None, max_length=500)
    result_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    gpu_memory_used: Optional[float] = None
    execution_time_seconds: Optional[float] = None
    ip_asset_id: Optional[int] = Field(None, description="Associated IP asset ID")


class TaskRecordResponse(TaskRecordBase):
    """Schema for task record response."""
    id: int
    task_id: str
    status: TaskStatus
    progress: float
    ip_asset_id: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None
    result_path: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int
    gpu_memory_used: Optional[float] = None
    execution_time_seconds: Optional[float] = None
    created_by: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for paginated task list."""
    total: int = Field(..., description="Total count")
    items: List[TaskRecordResponse] = Field(..., description="Tasks")


class TaskStatistics(BaseModel):
    """Schema for task statistics."""
    total_tasks: int
    pending_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    average_execution_time: Optional[float] = None
