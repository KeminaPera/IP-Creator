"""
Task Router

API endpoints for task monitoring and management.
Includes SSE for real-time progress updates.
"""
import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.config.database import get_db_session
from app.models.task import TaskRecord
from app.models.ip_asset import IPAsset
from app.models.generated_content import GeneratedContent
from app.api.deps import get_current_user
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    AppException
)
from app.utils.response import success_response, list_response, created_response, updated_response, deleted_response, message_response
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.get("/stream")
async def stream_task_updates(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    SSE endpoint for real-time task progress updates.
    
    Streams task status changes to connected clients.
    """
    async def event_generator():
        last_task_count = 0
        
        while True:
            try:
                # Query latest task states
                result = await db.execute(
                    select(TaskRecord).where(
                        TaskRecord.created_by == current_user["username"]
                    ).order_by(TaskRecord.updated_at.desc()).limit(20)
                )
                tasks = result.scalars().all()
                
                # Check if there are changes
                current_count = len(tasks)
                if current_count != last_task_count or any(t.status in ["running", "completed", "failed"] for t in tasks):
                    last_task_count = current_count
                    
                    # Format task data
                    task_data = []
                    for task in tasks:
                        task_data.append({
                            "id": task.id,
                            "task_type": task.task_type,
                            "status": task.status,
                            "progress": task.progress,
                            "error_message": task.error_message,
                            "updated_at": task.created_at.isoformat() if task.created_at else None,
                        })
                    
                    yield f"data: {json.dumps({'tasks': task_data})}\n\n"
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"SSE error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/list")
async def list_tasks(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    task_type: Optional[str] = None,
    ip_asset_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    List tasks with pagination and filtering.
    """
    try:
        # Build query
        query = select(TaskRecord)
        count_query = select(func.count(TaskRecord.id))
        
        if status_filter:
            query = query.where(TaskRecord.status == status_filter)
            count_query = count_query.where(TaskRecord.status == status_filter)
        
        if task_type:
            query = query.where(TaskRecord.task_type == task_type)
            count_query = count_query.where(TaskRecord.task_type == task_type)
        
        if ip_asset_id:
            query = query.where(TaskRecord.ip_asset_id == ip_asset_id)
            count_query = count_query.where(TaskRecord.ip_asset_id == ip_asset_id)
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get items with pagination - sort by created_at descending
        query = query.offset(skip).limit(limit).order_by(TaskRecord.created_at.desc())
        result = await db.execute(query)
        items = result.scalars().all()
        
        # Fetch IP asset info for tasks
        ip_ids = [t.ip_asset_id for t in items if t.ip_asset_id]
        ip_map = {}
        if ip_ids:
            ip_result = await db.execute(
                select(IPAsset.id, IPAsset.name).where(IPAsset.id.in_(ip_ids))
            )
            ip_map = {row[0]: row[1] for row in ip_result.all()}
        
        # Convert to dict for response
        task_list = []
        for task in items:
            task_list.append({
                "id": task.id,
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "progress": task.progress,
                "ip_asset_id": task.ip_asset_id,
                "ip_name": ip_map.get(task.ip_asset_id) if task.ip_asset_id else None,
                "result": task.result_path,
                "error_message": task.error_message,
                "created_by": task.created_by,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            })
        
        # Get stats
        stats_query = select(
            TaskRecord.status,
            func.count(TaskRecord.id)
        ).group_by(TaskRecord.status)
        
        if ip_asset_id:
            stats_query = stats_query.where(TaskRecord.ip_asset_id == ip_asset_id)
        
        stats_result = await db.execute(stats_query)
        stats = dict(stats_result.all())
        
        # Calculate page info from skip/limit
        page = (skip // limit) + 1 if limit > 0 else 1
        page_size = limit
        
        return list_response(
            items=task_list,
            page=page,
            page_size=page_size,
            total=total,
            meta={"stats": stats}
        )
        
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to list tasks"
        )


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get a specific task by Celery task ID (UUID) or database primary key.

    同时兼容两种调用:
    - /tasks/<celery-uuid>  -> 按 TaskRecord.task_id 查
    - /tasks/<integer-id>   -> 按 TaskRecord.id   查 (供前端列表中 row.id 使用)
    """
    try:
        # 纯数字优先按主键查; 未命中再回退按 Celery task_id 查
        task = None
        if task_id.isdigit():
            result = await db.execute(
                select(TaskRecord).where(TaskRecord.id == int(task_id))
            )
            task = result.scalar_one_or_none()
        if task is None:
            result = await db.execute(
                select(TaskRecord).where(TaskRecord.task_id == task_id)
            )
            task = result.scalar_one_or_none()

        if not task:
            raise NotFoundException(resource="Task", identifier=task_id)
        
        # Fetch IP asset name if ip_asset_id exists
        ip_name = None
        if task.ip_asset_id:
            ip_result = await db.execute(
                select(IPAsset.name).where(IPAsset.id == task.ip_asset_id)
            )
            ip_row = ip_result.scalar_one_or_none()
            if ip_row:
                ip_name = ip_row
        
        return success_response(
            data={
                "id": task.id,
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "progress": task.progress,
                "result_path": task.result_path,
                "result_metadata": task.result_metadata,
                "error_message": task.error_message,
                "created_by": task.created_by,
                "ip_asset_id": task.ip_asset_id,
                "ip_name": ip_name,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "execution_time_seconds": task.execution_time_seconds,
                "channel_id": task.channel_id,
            }
        )
        
    except NotFoundException:
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to get task"
        )


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retry a failed task.
    """
    try:
        result = await db.execute(
            select(TaskRecord).where(TaskRecord.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise NotFoundException(resource="Task", identifier=str(task_id))
        
        if task.status != "failed":
            raise BadRequestException(message="Only failed tasks can be retried")
        
        # Reset task status
        task.status = "pending"
        task.progress = 0
        task.error_message = None
        
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Task {task_id} reset to pending by user {current_user['username']}")
        
        return message_response(
            message="Task reset to pending",
            data={"task_id": task_id}
        )
        
    except (NotFoundException, BadRequestException):
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to retry task"
        )


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Delete a task record.
    """
    try:
        result = await db.execute(
            select(TaskRecord).where(TaskRecord.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise NotFoundException(resource="Task", identifier=str(task_id))
        
        # Delete the task
        await db.delete(task)
        await db.commit()
        
        logger.info(f"Task {task_id} deleted by user {current_user['username']}")
        
        return deleted_response(
            resource_id=task_id,
            message="Task deleted successfully"
        )
        
    except NotFoundException:
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to delete task"
        )


@router.get("/{task_id}/content-result")
async def get_task_content_result(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get all generated content associated with a task.
    
    Returns all content items if the task produced generated content
    (image, video, story). Returns has_content=False for tasks like LoRA training.
    
    Supports both database ID and Celery task ID (UUID).
    """
    try:
        # Support both database ID (integer) and Celery task ID (UUID)
        # Same logic as get_task endpoint
        task = None
        if task_id.isdigit():
            result = await db.execute(
                select(TaskRecord).where(TaskRecord.id == int(task_id))
            )
            task = result.scalar_one_or_none()
        if task is None:
            result = await db.execute(
                select(TaskRecord).where(TaskRecord.task_id == task_id)
            )
            task = result.scalar_one_or_none()
        
        if not task:
            raise NotFoundException(resource="Task", identifier=task_id)
        
        logger.info(f"Looking for content with task_id: {task.task_id} (task type: {task.task_type}, status: {task.status})")
        
        # Query ALL generated content by task_id (Celery task ID)
        # A single task may produce multiple content items (story + images + video)
        content_result = await db.execute(
            select(GeneratedContent).where(GeneratedContent.task_id == task.task_id)
        )
        contents = content_result.scalars().all()
        
        if not contents:
            logger.warning(f"No content found for task_id: {task.task_id}")
            return success_response(
                data={
                    "has_content": False,
                    "message": "No generated content found for this task",
                }
            )
        
        logger.info(f"Found {len(contents)} content items for task_id: {task.task_id}")
        
        # Return all content items
        content_list = []
        for content in contents:
            content_list.append({
                "content_id": content.id,
                "content_type": content.content_type,  # story, image, video
                "title": content.title,
                "description": content.description,
                "file_path": content.file_path,
                "thumbnail_path": content.thumbnail_path,
                "file_size": content.file_size,
                "duration_seconds": content.duration_seconds,
                "resolution": content.resolution,
                "word_count": content.word_count,
                "status": content.status,
                "is_favorite": content.is_favorite,
                "created_at": content.created_at.isoformat() if content.created_at else None,
            })
        
        return success_response(
            data={
                "has_content": True,
                "task_id": task.task_id,
                "task_type": task.task_type,
                "content_count": len(content_list),
                "contents": content_list,
            }
        )
        
    except NotFoundException:
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to get task content result"
        )
