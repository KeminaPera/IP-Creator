# 统一错误处理使用指南

## 📋 概述

项目已实现统一的错误处理系统，所有API错误响应现在遵循一致的结构。

---

## 🎯 错误响应格式

### **统一响应结构**

```json
{
  "success": false,
  "error": {
    "error": "ErrorType",
    "message": "Human-readable message",
    "code": "MACHINE_READABLE_CODE",
    "details": null,
    "request_id": "req_abc123"
  }
}
```

### **字段说明**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `success` | boolean | ✅ | 始终为 `false`（错误响应） |
| `error.error` | string | ✅ | 错误类型（如 `NotFoundError`） |
| `error.message` | string | ✅ | 人类可读的错误信息 |
| `error.code` | string | ❌ | 机器可读的错误代码（可选） |
| `error.details` | any | ❌ | 额外错误详情（验证错误等） |
| `error.request_id` | string | ❌ | 请求追踪ID（用于调试） |

---

## 🚀 使用方式

### **方式1：使用预定义的异常类（推荐）**

```python
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    ConflictException,
    ValidationException
)

# ❌ 旧方式（不统一）
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="Content not found")

# ✅ 新方式（统一格式）
raise NotFoundException(resource="Content", identifier=content_id)
```

### **方式2：使用自定义AppException**

```python
from app.core.exceptions import AppException

raise AppException(
    status_code=400,
    error="CustomError",
    message="Custom error message",
    code="CUSTOM_ERROR_CODE",
    details={"extra": "info"}
)
```

### **方式3：手动创建错误响应**

```python
from app.core.exceptions import create_error_response

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    try:
        item = await db.get(Item, item_id)
        if not item:
            return create_error_response(
                status_code=404,
                error="NotFoundError",
                message=f"Item {item_id} not found",
                code="ITEM_NOT_FOUND"
            )
        return {"success": True, "data": item}
    except Exception as e:
        return create_error_response(
            status_code=500,
            error="DatabaseError",
            message="Failed to query item",
            details=str(e)
        )
```

---

## 📚 预定义异常类

### **1. NotFoundException (404)**

```python
# 简单用法
raise NotFoundException(resource="Content")

# 带标识符
raise NotFoundException(resource="Content", identifier=content_id)
raise NotFoundException(resource="User", identifier=user_id)
```

**响应示例**：
```json
{
  "success": false,
  "error": {
    "error": "NotFoundError",
    "message": "Content with identifier '123' not found",
    "code": "CONTENT_NOT_FOUND",
    "details": null,
    "request_id": null
  }
}
```

---

### **2. BadRequestException (400)**

```python
# 简单用法
raise BadRequestException(message="Invalid request parameters")

# 带详情
raise BadRequestException(
    message="Invalid date range",
    details={"start_date": "2024-01-01", "end_date": "2023-01-01"}
)
```

---

### **3. UnauthorizedException (401)**

```python
raise UnauthorizedException(message="Invalid credentials")
raise UnauthorizedException(message="Token expired")
```

---

### **4. ForbiddenException (403)**

```python
raise ForbiddenException(message="Insufficient permissions")
raise ForbiddenException(message="Access denied for this resource")
```

---

### **5. ConflictException (409)**

```python
raise ConflictException(message="Username already exists")
raise ConflictException(message="Resource version conflict")
```

---

### **6. ValidationException (422)**

```python
raise ValidationException(
    message="Validation failed",
    details=[
        {"field": "email", "message": "Invalid email format"},
        {"field": "password", "message": "Password too short"}
    ]
)
```

---

## 🔄 迁移指南

### **Step 1: 更新现有HTTPException**

**旧代码**：
```python
from fastapi import HTTPException, status

@router.get("/{content_id}")
async def get_content(content_id: int):
    content = await db.get(Content, content_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content with ID {content_id} not found"
        )
```

**新代码**：
```python
from app.core.exceptions import NotFoundException

@router.get("/{content_id}")
async def get_content(content_id: int):
    content = await db.get(Content, content_id)
    if not content:
        raise NotFoundException(resource="Content", identifier=content_id)
```

---

### **Step 2: 更新错误返回字典**

**旧代码**：
```python
@app.post("/generate")
async def generate_content():
    try:
        result = await generate()
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
```

**新代码**：
```python
from app.core.exceptions import AppException

@app.post("/generate")
async def generate_content():
    try:
        result = await generate()
        return {"success": True, "data": result}
    except Exception as e:
        raise AppException(
            status_code=500,
            error="GenerationError",
            message="Failed to generate content",
            details=str(e)
        )
```

---

### **Step 3: 更新服务层错误**

**旧代码（cloud_gen_service.py）**：
```python
def generate_image():
    try:
        response = await api.call()
        return {"status": "success", "data": response}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
```

**新代码**：
```python
from app.core.exceptions import AppException

def generate_image():
    try:
        response = await api.call()
        return {"success": True, "data": response}
    except Exception as e:
        raise AppException(
            status_code=500,
            error="APIError",
            message="Failed to call image generation API",
            details=str(e)
        )
```

---

## 🎨 实际示例

### **示例1：内容库API**

```python
from fastapi import APIRouter, Depends
from app.core.exceptions import NotFoundException, BadRequestException

@router.get("/{content_id}")
async def get_content(content_id: int, db: AsyncSession = Depends(get_db)):
    """获取内容详情"""
    content = await db.get(GeneratedContent, content_id)
    
    if not content:
        raise NotFoundException(resource="Content", identifier=content_id)
    
    return {"success": True, "data": content}

@router.delete("/{content_id}")
async def delete_content(content_id: int, db: AsyncSession = Depends(get_db)):
    """删除内容"""
    content = await db.get(GeneratedContent, content_id)
    
    if not content:
        raise NotFoundException(resource="Content", identifier=content_id)
    
    if content.status == "deleted":
        raise BadRequestException(message="Content already deleted")
    
    content.status = "deleted"
    await db.commit()
    
    return {"success": True, "message": "Content deleted"}
```

---

### **示例2：任务监控API**

```python
from app.core.exceptions import NotFoundException, ConflictException

@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """取消任务"""
    task = await db.execute(
        select(TaskRecord).where(TaskRecord.task_id == task_id)
    )
    task = task.scalar_one_or_none()
    
    if not task:
        raise NotFoundException(resource="Task", identifier=task_id)
    
    if task.status not in ["pending", "running"]:
        raise ConflictException(
            message=f"Cannot cancel task in '{task.status}' state",
            details={"current_status": task.status}
        )
    
    task.status = "cancelled"
    await db.commit()
    
    return {"success": True, "message": "Task cancelled"}
```

---

### **示例3：IP资产API**

```python
from app.core.exceptions import NotFoundException, ConflictException, BadRequestException

@router.put("/{ip_id}")
async def update_ip(ip_id: int, data: IPUpdateSchema, db: AsyncSession = Depends(get_db)):
    """更新IP资产"""
    ip_asset = await db.get(IPAsset, ip_id)
    
    if not ip_asset:
        raise NotFoundException(resource="IPAsset", identifier=ip_id)
    
    # 检查trigger_word是否已被其他IP使用
    if data.trigger_word:
        existing = await db.execute(
            select(IPAsset).where(
                IPAsset.trigger_word == data.trigger_word,
                IPAsset.id != ip_id
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictException(
                message=f"Trigger word '{data.trigger_word}' already in use",
                details={"field": "trigger_word"}
            )
    
    # 更新字段
    for field, value in data.dict(exclude_unset=True).items():
        setattr(ip_asset, field, value)
    
    await db.commit()
    
    return {"success": True, "data": ip_asset}
```

---

## 📊 错误响应对比

### **统一前（混乱）**

```json
// 有些地方返回
{"detail": "Not found"}

// 有些地方返回
{"error": "message", "detail": "..."}

// 有些地方返回
{"status": "failed", "error": "..."}

// 有些地方返回
{"message": "Error occurred"}
```

### **统一后（一致）**

```json
{
  "success": false,
  "error": {
    "error": "NotFoundError",
    "message": "Content with identifier '123' not found",
    "code": "CONTENT_NOT_FOUND",
    "details": null,
    "request_id": "req_abc123"
  }
}
```

---

## 🔍 前端处理示例

### **Vue 3 + Axios**

```javascript
// api.js
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1'
})

// 统一错误处理
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.data?.error) {
      const { error: errorObj } = error.response.data
      
      // 显示错误消息
      ElMessage.error(errorObj.message)
      
      // 根据错误类型处理
      switch (errorObj.code) {
        case 'CONTENT_NOT_FOUND':
          router.push('/404')
          break
        case 'UNAUTHORIZED':
          router.push('/login')
          break
        case 'RATE_LIMIT_EXCEEDED':
          // 等待后重试
          setTimeout(() => retryRequest(error.config), 1000)
          break
      }
    }
    
    return Promise.reject(error)
  }
)

export default api
```

---

### **TypeScript 类型定义**

```typescript
// types/api.ts
export interface APIError {
  error: string          // Error type
  message: string        // Human-readable message
  code?: string          // Machine-readable code
  details?: any          // Additional details
  request_id?: string    // Request tracking ID
}

export interface APIResponse<T = any> {
  success: boolean
  error?: APIError
  data?: T
}

// 使用示例
async function getContent(id: number): Promise<Content> {
  const response = await api.get<APIResponse<Content>>(`/contents/${id}`)
  
  if (!response.data.success) {
    throw new Error(response.data.error?.message)
  }
  
  return response.data.data!
}
```

---

## ✅ 最佳实践

### **1. 使用预定义异常类**

```python
# ✅ 推荐
raise NotFoundException(resource="Content", identifier=content_id)

# ❌ 不推荐
raise HTTPException(status_code=404, detail="Not found")
```

---

### **2. 提供有意义的错误信息**

```python
# ✅ 推荐
raise NotFoundException(
    resource="Content",
    identifier=content_id
)

# ❌ 不推荐（信息不足）
raise NotFoundException()
```

---

### **3. 使用details字段传递额外信息**

```python
# ✅ 推荐
raise BadRequestException(
    message="Invalid date range",
    details={
        "start_date": start_date,
        "end_date": end_date,
        "reason": "end_date must be after start_date"
    }
)
```

---

### **4. 不要暴露敏感信息**

```python
# ✅ 推荐
raise AppException(
    status_code=500,
    error="DatabaseError",
    message="Failed to query database"
)

# ❌ 不推荐（暴露SQL详情）
raise AppException(
    status_code=500,
    error="DatabaseError",
    message="SQL: SELECT * FROM contents WHERE id=123; Error: table not found"
)
```

---

### **5. 在日志中记录完整错误**

```python
# 异常处理器已自动记录
logger.error(
    f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
    exc_info=True  # 包含堆栈跟踪
)
```

---

## 📈 优势

1. ✅ **一致性** - 所有API错误遵循相同格式
2. ✅ **可维护性** - 集中管理错误类型和消息
3. ✅ **可调试性** - 包含request_id和详细日志
4. ✅ **前端友好** - 统一错误处理逻辑
5. ✅ **国际化支持** - message字段可轻松翻译
6. ✅ **机器可读** - code字段用于程序化处理
7. ✅ **扩展性** - 轻松添加新错误类型

---

## 🎯 下一步

1. **迁移现有代码** - 逐步替换所有 `HTTPException` 和错误字典
2. **前端适配** - 更新前端错误处理逻辑
3. **添加单元测试** - 测试各种错误场景
4. **监控告警** - 基于错误类型设置告警规则
