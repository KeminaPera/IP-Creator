"""
Resource Management Router

Provides unified resource upload, delete, and access APIs.
All files are stored in data/resources/{year}/{month}/{day}/ with UUID prefix.
"""
from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import os
import mimetypes
from datetime import datetime
from urllib.parse import unquote

from app.api.deps import get_current_user
from app.utils.response import success_response
from app.utils.logger import logger
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException, InternalServerError, AppException

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])

# 资源存储根目录
RESOURCE_BASE = Path("data/resources")

# 文件大小限制（50MB）
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload")
async def upload_resource(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    统一资源上传接口
    
    - 自动按日期创建文件夹
    - 使用UUID + 原文件名命名
    - 验证文件大小
    - 返回资源路径和元信息
    """
    try:
        # 1. 验证文件名
        if not file.filename:
            raise BadRequestException("Filename is required")
        
        # 2. 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 3. 验证文件大小
        if file_size > MAX_FILE_SIZE:
            raise BadRequestException(
                f"File size {file_size} exceeds limit ({MAX_FILE_SIZE})"
            )
        
        if file_size == 0:
            raise BadRequestException("Empty file")
        
        # 4. 提取文件信息
        original_name = file.filename
        extension = Path(original_name).suffix.lower()
        mime_type = file.content_type or "application/octet-stream"
        
        # 5. 生成存储路径
        now = datetime.now()
        date_folder = RESOURCE_BASE / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        
        # 6. 创建目录
        date_folder.mkdir(parents=True, exist_ok=True)
        
        # 7. 生成唯一文件名
        file_uuid = uuid.uuid4().hex[:12]
        file_name = f"{file_uuid}_{original_name}"
        file_path = date_folder / file_name
        
        # 8. 保存文件
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # 9. 构建响应
        relative_path = str(file_path.relative_to(Path(".")))
        # URL编码路径，确保特殊字符正确处理
        from urllib.parse import quote
        encoded_path = quote(relative_path, safe='')
        resource_url = f"/api/v1/resources/{encoded_path}"
        
        logger.info(
            f"Resource uploaded: {relative_path}, "
            f"size: {file_size}, user: {current_user.get('username')}"
        )
        
        return success_response(
            data={
                "resource_path": relative_path,
                "resource_url": resource_url,
                "original_name": original_name,
                "file_size": file_size,
                "mime_type": mime_type,
                "extension": extension,
                "upload_time": now.isoformat()
            },
            message="Resource uploaded successfully"
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Resource upload failed: {e}", exc_info=True)
        raise InternalServerError(message=f"Upload failed: {str(e)}")


@router.delete("/{resource_path:path}")
async def delete_resource(
    resource_path: str,
    current_user: dict = Depends(get_current_user)
):
    """
    统一资源删除接口
    
    - 验证路径合法性
    - 验证文件存在性
    - 物理删除文件
    - 安全检查：防止路径遍历攻击
    """
    try:
        # 1. 解码路径
        resource_path = unquote(resource_path)
        
        # 2. 安全检查：使用 resolve() 防御路径遍历攻击
        full_path = Path(resource_path).resolve()
        resource_base = Path("data/resources").resolve()
        
        # 确保文件在 resources 目录内（防御 ..\..\ 攻击）
        try:
            full_path.relative_to(resource_base)
        except ValueError:
            raise ForbiddenException(message="Invalid resource path")
        
        # 3. 验证文件存在
        if not full_path.exists():
            raise NotFoundException(resource="Resource", identifier=resource_path)
        
        if not full_path.is_file():
            raise BadRequestException("Not a file")
        
        # 4. 删除文件
        full_path.unlink()
        
        logger.info(
            f"Resource deleted: {resource_path}, "
            f"user: {current_user.get('username')}"
        )
        
        return success_response(
            data={"resource_path": resource_path},
            message="Resource deleted successfully"
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Resource delete failed: {e}", exc_info=True)
        raise InternalServerError(message=f"Delete failed: {str(e)}")


@router.get("/{resource_path:path}")
async def get_resource(resource_path: str):
    """
    统一资源访问接口
    
    - 返回文件二进制流
    - 设置正确的Content-Type
    - 支持浏览器预览
    - 支持缓存
    """
    try:
        # 1. 解码路径
        resource_path = unquote(resource_path)
        
        # 2. 安全检查：使用 resolve() 防御路径遍历攻击
        full_path = Path(resource_path).resolve()
        resource_base = Path("data/resources").resolve()
        
        # 确保文件在 resources 目录内（防御 ..\..\ 攻击）
        try:
            full_path.relative_to(resource_base)
        except ValueError:
            raise ForbiddenException(message="Invalid resource path")
        
        # 3. 验证文件存在
        if not full_path.exists():
            raise NotFoundException(resource="Resource", identifier=resource_path)
        
        if not full_path.is_file():
            raise BadRequestException("Not a file")
        
        # 4. 获取MIME类型
        mime_type, _ = mimetypes.guess_type(str(full_path))
        mime_type = mime_type or "application/octet-stream"
        
        # 5. 提取原始文件名（去掉UUID前缀）
        original_name = "_".join(full_path.name.split("_")[1:])
        
        # 6. 返回文件
        return FileResponse(
            path=str(full_path),
            media_type=mime_type,
            filename=original_name,
            headers={
                "Cache-Control": "public, max-age=31536000",  # 缓存1年
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Resource access failed: {e}", exc_info=True)
        raise InternalServerError(message=f"Access failed: {str(e)}")
