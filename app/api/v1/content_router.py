"""
Content Library Router

API endpoints for managing generated content (stories, images, videos).
Provides CRUD operations for the Content Library feature.
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from app.config.database import get_db_session
from app.models.generated_content import GeneratedContent
from app.models.ip_asset import IPAsset
from app.api.deps import get_current_user
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
    AppException
)
from app.utils.response import success_response, list_response, created_response, updated_response, deleted_response
from app.utils.logger import logger

router = APIRouter(prefix="/api/v1/contents", tags=["Content Library"])


@router.get("")
async def list_contents(
    content_type: Optional[str] = Query(None, description="Filter by content type: story, image, video"),
    task_id: Optional[str] = Query(None, description="Filter by Celery task ID (UUID)"),
    ip_asset_id: Optional[int] = Query(None, description="Filter by IP asset ID"),
    status: Optional[str] = Query("completed", description="Filter by status"),
    is_favorite: Optional[bool] = Query(None, description="Filter by favorite status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all generated contents with filtering and pagination."""
    try:
        # Build query
        query = select(GeneratedContent)
        count_query = select(func.count()).select_from(GeneratedContent)
        
        # Apply filters
        if content_type:
            query = query.where(GeneratedContent.content_type == content_type)
            count_query = count_query.where(GeneratedContent.content_type == content_type)
        
        if task_id:
            query = query.where(GeneratedContent.task_id == task_id)
            count_query = count_query.where(GeneratedContent.task_id == task_id)
        
        if ip_asset_id:
            query = query.where(GeneratedContent.ip_asset_id == ip_asset_id)
            count_query = count_query.where(GeneratedContent.ip_asset_id == ip_asset_id)
        
        if status:
            query = query.where(GeneratedContent.status == status)
            count_query = count_query.where(GeneratedContent.status == status)
        
        if is_favorite is not None:
            query = query.where(GeneratedContent.is_favorite == is_favorite)
            count_query = count_query.where(GeneratedContent.is_favorite == is_favorite)
        
        if start_date:
            query = query.where(GeneratedContent.created_at >= start_date)
            count_query = count_query.where(GeneratedContent.created_at >= start_date)
        
        if end_date:
            query = query.where(GeneratedContent.created_at <= end_date)
            count_query = count_query.where(GeneratedContent.created_at <= end_date)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (GeneratedContent.title.like(search_pattern)) |
                (GeneratedContent.description.like(search_pattern))
            )
            count_query = count_query.where(
                (GeneratedContent.title.like(search_pattern)) |
                (GeneratedContent.description.like(search_pattern))
            )
        
        # Filter by tags (JSON array contains any of the specified tags)
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            if tag_list:
                # Use JSON containment operator for SQLite
                for tag in tag_list:
                    query = query.where(GeneratedContent.tags.contains(f'"{tag}"'))
                    count_query = count_query.where(GeneratedContent.tags.contains(f'"{tag}"'))
        
        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(GeneratedContent.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        contents = result.scalars().all()
        
        # Convert to dict
        content_list = []
        for content in contents:
            content_dict = {
                "id": content.id,
                "task_id": content.task_id,
                "task_type": content.task_type,
                "content_type": content.content_type,
                "title": content.title,
                "description": content.description,
                "file_path": content.file_path,
                "thumbnail_path": content.thumbnail_path,
                "file_size": content.file_size,
                "duration_seconds": content.duration_seconds,
                "resolution": content.resolution,
                "word_count": content.word_count,
                "ip_asset_id": content.ip_asset_id,
                "parameters": content.parameters,
                "content_metadata": content.content_metadata,
                "tags": content.tags,
                "is_favorite": content.is_favorite,
                "status": content.status,
                "error_message": content.error_message,
                "execution_time_seconds": content.execution_time_seconds,
                "channel_id": content.channel_id,
                "created_at": content.created_at,
                "updated_at": content.updated_at,
            }
            content_list.append(content_dict)
        
        return list_response(
            items=content_list,
            page=page,
            page_size=page_size,
            total=total
        )
    
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to list contents"
        )


@router.get("/stats")
async def get_content_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get content statistics (count by type, status, etc.)."""
    try:
        # Count by content type
        type_query = select(
            GeneratedContent.content_type,
            func.count().label('count')
        ).group_by(GeneratedContent.content_type)
        type_result = await db.execute(type_query)
        type_stats = {row[0]: row[1] for row in type_result.all()}
        
        # Count by status
        status_query = select(
            GeneratedContent.status,
            func.count().label('count')
        ).group_by(GeneratedContent.status)
        status_result = await db.execute(status_query)
        status_stats = {row[0]: row[1] for row in status_result.all()}
        
        # Total favorites
        fav_query = select(func.count()).where(GeneratedContent.is_favorite == True)
        fav_result = await db.execute(fav_query)
        favorite_count = fav_result.scalar()
        
        # Total count
        total_query = select(func.count()).where(GeneratedContent.status == "completed")
        total_result = await db.execute(total_query)
        total_count = total_result.scalar()
        
        return success_response(
            data={
                "total": total_count,
                "by_type": type_stats,
                "by_status": status_stats,
                "favorites": favorite_count,
            }
        )
    
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to get content statistics"
        )


@router.get("/{content_id}")
async def get_content(
    content_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get detailed information about a specific content."""
    try:
        result = await db.execute(
            select(GeneratedContent).where(GeneratedContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        
        if not content:
            raise NotFoundException(resource="Content", identifier=str(content_id))
        
        return success_response(
            data={
                "id": content.id,
                "task_id": content.task_id,
                "task_type": content.task_type,
                "content_type": content.content_type,
                "title": content.title,
                "description": content.description,
                "file_path": content.file_path,
                "thumbnail_path": content.thumbnail_path,
                "file_size": content.file_size,
                "duration_seconds": content.duration_seconds,
                "resolution": content.resolution,
                "word_count": content.word_count,
                "ip_asset_id": content.ip_asset_id,
                "parameters": content.parameters,
                "content_metadata": content.content_metadata,
                "tags": content.tags,
                "is_favorite": content.is_favorite,
                "status": content.status,
                "error_message": content.error_message,
                "execution_time_seconds": content.execution_time_seconds,
                "channel_id": content.channel_id,
                "created_at": content.created_at,
                "updated_at": content.updated_at,
            }
        )
    
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to get content"
        )


@router.put("/{content_id}")
async def update_content(
    content_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update content metadata (title, description, tags)."""
    try:
        result = await db.execute(
            select(GeneratedContent).where(GeneratedContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        
        if not content:
            raise NotFoundException(resource="Content", identifier=str(content_id))
        
        # Update fields
        if title is not None:
            content.title = title
        if description is not None:
            content.description = description
        if tags is not None:
            content.tags = tags
        
        await db.commit()
        await db.refresh(content)
        
        return updated_response(
            data={
                "id": content.id,
                "title": content.title,
                "description": content.description,
                "tags": content.tags,
            },
            message="Content updated successfully"
        )
    
    except NotFoundException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to update content"
        )


@router.post("/{content_id}/favorite")
async def toggle_favorite(
    content_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Toggle content favorite status."""
    try:
        result = await db.execute(
            select(GeneratedContent).where(GeneratedContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        
        if not content:
            raise NotFoundException(resource="Content", identifier=str(content_id))
        
        content.is_favorite = not content.is_favorite
        await db.commit()
        
        return success_response(
            data={
                "id": content.id,
                "is_favorite": content.is_favorite,
            },
            message="Favorite status updated"
        )
    
    except NotFoundException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to update favorite status"
        )


@router.delete("/{content_id}")
async def delete_content(
    content_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a content record (soft delete - marks as deleted)."""
    try:
        result = await db.execute(
            select(GeneratedContent).where(GeneratedContent.id == content_id)
        )
        content = result.scalar_one_or_none()
        
        if not content:
            raise NotFoundException(resource="Content", identifier=str(content_id))
        
        # Soft delete
        content.status = "deleted"
        await db.commit()
        
        return deleted_response(
            resource_id=content_id,
            message="Content deleted successfully"
        )
    
    except NotFoundException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise AppException(
            status_code=500,
            error="DatabaseError",
            message="Failed to delete content"
        )


@router.get("/files/{file_path:path}")
async def serve_content_file(
    file_path: str,
):
    """
    Serve content files (stories, images, videos).
    
    This endpoint serves files from the data directory with proper security checks.
    """
    try:
        # Security: Prevent directory traversal attacks
        if '..' in file_path or file_path.startswith('/'):
            raise BadRequestException(message="Invalid file path")
        
        # Normalize path separators (Windows backslash to forward slash)
        file_path = file_path.replace('\\', '/')
        
        # Construct full file path
        # Handle both cases:
        # 1. file_path already starts with 'data/' -> use as relative to project root
        # 2. file_path is just the subpath -> prepend './data/'
        if file_path.startswith('data/') or file_path.startswith('data\\'):
            # Already includes 'data' prefix, ensure it starts with './'
            full_path = Path('./' + file_path)
        else:
            # Need to add 'data' prefix
            base_dir = Path('./data')
            full_path = base_dir / file_path
        
        # Verify file exists and is within data directory
        full_path = full_path.resolve()
        if not full_path.exists():
            raise NotFoundException(resource="File")
        
        if not full_path.is_file():
            raise BadRequestException(message="Path is not a file")
        
        # Security check: ensure file is within data directory
        data_dir = Path('./data').resolve()
        # Use is_relative_to() for Python 3.9+, or check with resolved paths
        try:
            full_path.relative_to(data_dir)
        except ValueError:
            raise ForbiddenException(message="Access denied")
        
        # Determine media type
        suffix = full_path.suffix.lower()
        media_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.avi': 'video/avi',
        }
        
        media_type = media_types.get(suffix, 'application/octet-stream')
        
        return FileResponse(
            path=str(full_path),
            media_type=media_type,
            filename=full_path.name
        )
    
    except (NotFoundException, BadRequestException, ForbiddenException):
        raise
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        raise AppException(
            status_code=500,
            error="FileError",
            message="Failed to serve file"
        )
