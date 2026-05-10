# API Reference Documentation

## Overview

IP Creator provides a comprehensive RESTful API with unified response format across all endpoints. All APIs are prefixed with `/api/v1` and require JWT authentication unless otherwise noted.

---

## Table of Contents

- [Unified Response Format](#unified-response-format)
- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [API Endpoints](#api-endpoints)
  - [Authentication APIs](#authentication-apis)
  - [LLM Management APIs](#llm-management-apis)
  - [Provider Management APIs](#provider-management-apis)
  - [IP Asset APIs](#ip-asset-apis)
  - [LoRA Model APIs](#lora-model-apis)
  - [Generation APIs](#generation-apis)
  - [Task Management APIs](#task-management-apis)
  - [Content Library APIs](#content-library-apis)
  - [Settings APIs](#settings-apis)
  - [System Health APIs](#system-health-apis)
  - [Dashboard APIs](#dashboard-apis)

---

## Unified Response Format

All API responses follow a standardized format:

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful",
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 100
  },
  "meta": {
    "timestamp": "2026-05-07T12:00:00Z",
    "request_id": "req_123456"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "error": "ValidationError",
    "message": "Request validation failed",
    "code": "VALIDATION_ERROR",
    "details": [
      {
        "field": "body.name",
        "message": "Field required",
        "type": "missing"
      }
    ],
    "request_id": "req_123456"
  }
}
```

### Response Helper Functions

| Helper | HTTP Status | Use Case |
|--------|-------------|----------|
| `success_response()` | 200 | General success responses |
| `created_response()` | 201 | Resource creation |
| `updated_response()` | 200 | Resource update |
| `deleted_response()` | 204 | Resource deletion |
| `list_response()` | 200 | Paginated lists |
| `message_response()` | 200 | Simple message responses |

---

## Authentication

### JWT Token Authentication

Most endpoints require a JWT access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

### Obtaining a Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin",
      "full_name": "System Administrator"
    }
  },
  "message": "Login successful"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful GET, PUT |
| 201 | Created | Successful POST (create) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource |
| 422 | Validation Error | Schema validation failed |
| 500 | Internal Server Error | Unexpected error |

### Error Types

| Error Type | Code | Description |
|------------|------|-------------|
| `ValidationError` | VALIDATION_ERROR | Request validation failed |
| `AuthenticationError` | AUTH_ERROR | Invalid credentials or token |
| `PermissionDeniedError` | PERMISSION_DENIED | Insufficient permissions |
| `ResourceNotFoundError` | NOT_FOUND | Resource not found |
| `ConflictError` | CONFLICT | Resource conflict |
| `InternalServerError` | INTERNAL_ERROR | Server error |

---

## API Endpoints

### Authentication APIs

#### POST `/api/v1/auth/login`

Login and obtain JWT access token.

**Request Body:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin",
      "full_name": "System Administrator"
    }
  },
  "message": "Login successful"
}
```

**No authentication required**

---

### LLM Management APIs

All LLM endpoints require **admin** role.

#### POST `/api/v1/llm/register`

Register a new LLM channel.

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "name": "智谱AI - GLM-4",
  "model_type": "cloud",
  "provider": "zhipu",
  "model_name": "glm-4",
  "api_endpoint": "https://open.bigmodel.cn/api/paas/v4",
  "api_key": "your-api-key",
  "temperature": 0.7,
  "max_tokens": 2048,
  "timeout": 120,
  "context_window": 128000
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": 10,
    "name": "智谱AI - GLM-4",
    "model_type": "cloud",
    "provider": "zhipu",
    "model_name": "glm-4"
  },
  "message": "LLM channel registered successfully"
}
```

#### GET `/api/v1/llm/list`

List all registered LLM channels.

**Authentication:** Required

**Query Parameters:**
- `skip` (int, default: 0): Offset
- `limit` (int, default: 50): Max items

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": 10,
      "name": "智谱AI - GLM-4",
      "model_type": "cloud",
      "provider": "zhipu",
      "model_name": "glm-4",
      "is_active": true,
      "health_status": "healthy",
      "response_time_ms": 1250
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 5
  }
}
```

#### PUT `/api/v1/llm/switch`

Switch active LLM model.

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "model_id": 10
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Switched active model to 智谱AI - GLM-4"
}
```

#### GET `/api/v1/llm/health/{model_id}`

Check health status of specific model.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "model_id": 10,
    "model_name": "glm-4",
    "health_status": "healthy",
    "response_time_ms": 1250,
    "error_message": null
  }
}
```

#### GET `/api/v1/llm/health/all`

Check health status of all models.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "model_id": 10,
      "model_name": "glm-4",
      "health_status": "healthy",
      "response_time_ms": 1250
    },
    {
      "model_id": 14,
      "model_name": "wan2.1-t2v",
      "health_status": "healthy",
      "response_time_ms": 2300
    }
  ]
}
```

#### GET `/api/v1/llm/channels/by-capability`

Get channels by capability.

**Authentication:** Required

**Query Parameters:**
- `capability` (string, required): text_generation, text_to_image, text_to_video

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": 10,
      "name": "智谱AI - GLM-4",
      "provider": "zhipu",
      "model_name": "glm-4",
      "capabilities": ["text_generation", "chat"]
    }
  ]
}
```

#### PUT `/api/v1/llm/switch`

Switch active LLM model.

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "model_id": 10
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Switched active model to 智谱AI - GLM-4"
}
```

#### PUT `/api/v1/llm/{model_id}`

Update LLM channel configuration.

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "name": "Updated Name",
  "api_key": "new-api-key",
  "temperature": 0.8,
  "is_active": true
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": 10,
    "name": "Updated Name",
    "temperature": 0.8,
    "is_active": true
  },
  "message": "LLM channel updated successfully"
}
```

#### DELETE `/api/v1/llm/{model_id}`

Delete LLM channel.

**Authentication:** Required (Admin)

**Response:** `204 No Content`
```json
{
  "success": true,
  "message": "LLM configuration deleted successfully"
}
```

#### POST `/api/v1/llm/providers/{provider_code}/sync-models`

Sync models from provider API.

**Authentication:** Required (Admin)

**Path Parameters:**
- `provider_code`: zhipu, dashscope, etc.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "synced": 5,
    "updated": 2,
    "failed": 0
  },
  "message": "Successfully synced 5 models"
}
```

---

### Provider Management APIs

All provider endpoints require **admin** role.

#### GET `/api/v1/providers`

List active providers with their models.

**Authentication:** Required (Admin)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": 5,
      "code": "zhipu",
      "name_cn": "智谱AI",
      "name_en": "Zhipu AI",
      "icon_class": "zhipu-icon",
      "is_active": true,
      "models": [
        {
          "id": 1,
          "code": "glm-4",
          "name": "GLM-4",
          "capabilities": ["text_generation", "chat"]
        }
      ]
    }
  ]
}
```

#### GET `/api/v1/providers/all`

List all providers (including inactive).

**Authentication:** Required (Admin)

**Response:** `200 OK`

*(Same structure as above)*

#### POST `/api/v1/providers`

Create new provider.

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "code": "openai",
  "name_cn": "OpenAI",
  "name_en": "OpenAI",
  "icon_class": "openai-icon",
  "website": "https://openai.com",
  "default_endpoint": "https://api.openai.com/v1",
  "requires_api_key": true
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": 10,
    "code": "openai",
    "name_cn": "OpenAI",
    "name_en": "OpenAI"
  },
  "message": "Provider created successfully"
}
```

#### PUT `/api/v1/providers/{provider_id}`

Update provider.

**Authentication:** Required (Admin)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": { ... },
  "message": "Provider updated successfully"
}
```

#### DELETE `/api/v1/providers/{provider_id}`

Delete provider.

**Authentication:** Required (Admin)

**Response:** `204 No Content`
```json
{
  "success": true,
  "message": "Provider deleted successfully"
}
```

#### GET `/api/v1/providers/{provider_id}/models`

Get models for specific provider.

**Authentication:** Required (Admin)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "code": "glm-4",
      "name": "GLM-4",
      "capabilities": ["text_generation", "chat"],
      "max_tokens": 128000,
      "is_active": true
    }
  ]
}
```

#### POST `/api/v1/models`

Create new model.

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "provider_id": 5,
  "code": "glm-4-plus",
  "name": "GLM-4 Plus",
  "capabilities": ["text_generation", "chat", "vision"],
  "max_tokens": 128000,
  "is_active": true
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": 20,
    "code": "glm-4-plus",
    "name": "GLM-4 Plus"
  },
  "message": "Model created successfully"
}
```

#### PUT `/api/v1/models/{model_id}`

Update model.

**Authentication:** Required (Admin)

**Response:** `200 OK`

#### DELETE `/api/v1/models/{model_id}`

Delete model.

**Authentication:** Required (Admin)

**Response:** `204 No Content`

---

### IP Asset APIs

#### POST `/api/v1/ip/create`

Create new IP asset.

**Authentication:** Required

**Request Body:**
```json
{
  "name": "小狐狸",
  "category": "pet",
  "trigger_word": "fox_character",
  "description": "A cute cartoon fox",
  "style_template": "3d_cartoon",
  "reference_images": [],
  "positive_tags": ["cute", "fluffy"],
  "negative_tags": ["realistic", "scary"],
  "lora_model_id": null
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": 7,
    "name": "小狐狸",
    "description": "A cute cartoon fox",
    "category": "pet",
    "trigger_word": "fox_character",
    "style_template": "3d_cartoon",
    "lora_model_id": null,
    "created_at": "2026-05-07T12:00:00",
    "updated_at": "2026-05-07T12:00:00"
  },
  "message": "IP asset created successfully"
}
```

#### GET `/api/v1/ip/list`

List IP assets.

**Authentication:** Required

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 100)
- `search` (string, optional): Search by name or trigger_word

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": 7,
      "name": "小狐狸",
      "category": "pet",
      "trigger_word": "fox_character",
      "style_template": "3d_cartoon",
      "description": "A cute cartoon fox",
      "reference_images": [],
      "lora_model_id": null
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 100,
    "total": 10
  }
}
```

#### GET `/api/v1/ip/{ip_id}`

Get IP asset details.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": 7,
    "name": "小狐狸",
    "category": "pet",
    "trigger_word": "fox_character",
    "style_template": "3d_cartoon",
    "description": "A cute cartoon fox",
    "reference_images": [
      {
        "angle": "front",
        "path": "uploads/ip_7/front.png"
      }
    ],
    "positive_tags": ["cute", "fluffy"],
    "negative_tags": ["realistic", "scary"],
    "lora_model_id": null,
    "created_at": "2026-05-07T12:00:00",
    "updated_at": "2026-05-07T12:00:00"
  }
}
```

#### PUT `/api/v1/ip/{ip_id}`

Update IP asset.

**Authentication:** Required

**Request Body:**
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "reference_images": [
    {
      "angle": "front",
      "path": "uploads/ip_7/front.png"
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": { ... },
  "message": "IP asset updated successfully"
}
```

#### DELETE `/api/v1/ip/{ip_id}`

Delete IP asset.

**Authentication:** Required

**Response:** `204 No Content`
```json
{
  "success": true,
  "message": "IP asset deleted successfully"
}
```

#### POST `/api/v1/ip/{ip_id}/generate-three-views`

Generate three views (front, side, back) for an IP asset.

**Authentication:** Required

**Path Parameters:**
- `ip_id`: IP asset ID

**Prerequisites:**
- IP asset must have reference images uploaded

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "task_ids": {
      "front": "task_id_1",
      "side": "task_id_2",
      "back": "task_id_3"
    },
    "message": "Three view generation tasks created"
  }
}
```

---

### LoRA Model APIs

#### POST `/api/v1/lora`

Create new LoRA training task.

**Authentication:** Required

**Request Body:**
```json
{
  "name": "Fox Character LoRA",
  "ip_asset_id": 7,
  "base_model": "stable-diffusion-v1-5",
  "training_params": {
    "max_train_steps": 2000,
    "learning_rate": 1e-4,
    "network_dim": 32
  }
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Fox Character LoRA",
    "status": "pending"
  },
  "message": "LoRA training task created"
}
```

#### GET `/api/v1/lora/list`

List LoRA models.

**Authentication:** Required

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 50)
- `status` (string, optional): pending, training, completed, failed

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Fox Character LoRA",
      "base_model": "stable-diffusion-v1-5",
      "status": "completed",
      "progress": 100.0,
      "current_loss": 0.05,
      "training_steps": 1000,
      "created_at": "2026-05-07T10:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 3
  }
}
```

#### GET `/api/v1/lora/{lora_id}`

Get LoRA training details.

**Authentication:** Required

**Response:** `200 OK`

#### PUT `/api/v1/lora/{lora_id}`

Update LoRA training configuration.

**Authentication:** Required

**Response:** `200 OK`

#### DELETE `/api/v1/lora/{lora_id}`

Delete LoRA training record.

**Authentication:** Required

**Response:** `204 No Content`

#### POST `/api/v1/lora/{lora_id}/cancel`

Cancel ongoing LoRA training.

**Authentication:** Required

**Response:** `200 OK`

---

### Generation APIs

#### POST `/api/v1/generate/story`

Generate story synchronously.

**Authentication:** Required

**Request Body:**
```json
{
  "prompt": "Create a healing story about friendship",
  "ip_name": "小狐狸",
  "style": "healing",
  "duration_seconds": 10,
  "channel_id": 10
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "story": "...",
    "title": "The Fox's Journey",
    "word_count": 850
  },
  "message": "Story generated successfully"
}
```

#### POST `/api/v1/generate/story/async`

Generate story asynchronously.

**Authentication:** Required

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "task_id": "80f2f57f-8864-4338-be7e-d1a5a12a3117",
    "task_type": "story_generation",
    "status": "pending"
  },
  "message": "Story generation task created"
}
```

#### POST `/api/v1/generate/image`

Generate image synchronously.

**Authentication:** Required

**Request Body:**
```json
{
  "prompt": "A cute fox in a forest",
  "ip_asset_id": 7,
  "channel_id": 15,
  "width": 512,
  "height": 512,
  "steps": 30,
  "cfg_scale": 7.5
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "image_path": "data/images/img_20260507_120000.png",
    "status": "success"
  },
  "message": "Image generated successfully"
}
```

#### POST `/api/v1/generate/image/async`

Generate image asynchronously.

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "task_id": "5b95c18c-5f0c-4885-a9f2-6f6dd4d92dff",
    "task_type": "image_generation",
    "status": "pending"
  }
}
```

#### POST `/api/v1/generate/video`

Generate video synchronously.

**Response:** `200 OK`

#### POST `/api/v1/generate/video/async`

Generate video asynchronously.

**Response:** `201 Created`

#### POST `/api/v1/generate/upload`

Upload file for generation.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "file_path": "uploads/reference/image.png"
  },
  "message": "File uploaded successfully"
}
```

#### GET `/api/v1/generate/files/{folder}/{filename}`

Access generated file.

**No authentication required**

---

### Task Management APIs

#### GET `/api/v1/tasks/list`

List tasks with pagination.

**Authentication:** Required

**Query Parameters:**
- `skip` (int, default: 0)
- `limit` (int, default: 10)
- `status` (string, optional): pending, running, completed, failed

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": 73,
      "task_id": "80f2f57f-8864-4338-be7e-d1a5a12a3117",
      "task_type": "story_generation",
      "status": "completed",
      "progress": 100.0,
      "ip_asset_id": 7,
      "created_at": "2026-05-07T04:32:15",
      "completed_at": "2026-05-07T04:33:24"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 75
  }
}
```

#### GET `/api/v1/tasks/{task_id}`

Get task details and status.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": 73,
    "task_id": "80f2f57f-8864-4338-be7e-d1a5a12a3117",
    "task_type": "story_generation",
    "status": "completed",
    "progress": 100.0,
    "result_path": "data/stories/story_123.json",
    "error_message": null,
    "started_at": "2026-05-07T04:32:20",
    "completed_at": "2026-05-07T04:33:24"
  }
}
```

#### PUT `/api/v1/tasks/{task_id}/cancel`

Cancel running task.

**Authentication:** Required

**Response:** `200 OK`

#### DELETE `/api/v1/tasks/{task_id}`

Delete task record.

**Authentication:** Required

**Response:** `204 No Content`

---

### Content Library APIs

#### GET `/api/v1/contents`

List generated content.

**Authentication:** Required

**Query Parameters:**
- `page` (int, default: 1)
- `page_size` (int, default: 10)
- `status` (string, optional): completed, failed
- `content_type` (string, optional): story, image, video

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "content_type": "story",
      "title": "The Fox's Journey",
      "file_path": "data/stories/story_20260507.json",
      "status": "completed",
      "created_at": "2026-05-07T12:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 25
  }
}
```

#### GET `/api/v1/contents/{content_id}`

Get content details.

**Response:** `200 OK`

#### POST `/api/v1/contents/{content_id}/favorite`

Toggle favorite status.

**Response:** `200 OK`

#### GET `/api/v1/contents/stats`

Get content statistics.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "total": 25,
    "by_type": {
      "story": 10,
      "image": 12,
      "video": 3
    },
    "by_status": {
      "completed": 23,
      "failed": 2
    },
    "favorites": 5
  }
}
```

#### DELETE `/api/v1/contents/{content_id}`

Delete content record and associated file.

**Authentication:** Required

**Response:** `204 No Content`

---

### Settings APIs

Manage system configuration settings.

#### GET `/api/v1/settings`

Get all settings grouped by category.

**Authentication:** Required (Admin)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "generation": {
      "max_concurrent_tasks": 2,
      "default_timeout": 300
    },
    "storage": {
      "models_path": "./data/models",
      "images_path": "./data/images"
    }
  }
}
```

#### GET `/api/v1/settings/{category}`

Get settings for specific category.

**Authentication:** Required (Admin)

**Path Parameters:**
- `category`: generation, storage, llm, system

**Response:** `200 OK`

#### GET `/api/v1/settings/{category}/{key}`

Get single setting value.

**Authentication:** Required (Admin)

**Response:** `200 OK`

#### PUT `/api/v1/settings/{category}/{key}`

Update setting value.

**Authentication:** Required (Admin)

**Request Body:**
```json
{
  "value": "new_value"
}
```

**Response:** `200 OK`

#### POST `/api/v1/settings/{category}/reset`

Reset all settings in category to defaults.

**Authentication:** Required (Admin)

**Response:** `200 OK`

#### GET `/api/v1/settings/categories`

List all available setting categories.

**Authentication:** Required (Admin)

**Response:** `200 OK`
```json
{
  "success": true,
  "data": ["generation", "storage", "llm", "system"]
}
```

---

### System Health APIs

Monitor system health status.

#### GET `/api/v1/health`

Comprehensive health check for all system components.

**No authentication required**

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "checks": {
      "redis": {
        "status": "ok",
        "message": "Redis connected",
        "latency_ms": 2
      },
      "database": {
        "status": "ok",
        "message": "Database accessible"
      },
      "llm_configs": {
        "status": "ok",
        "message": "3 LLM config(s) ready",
        "count": 3,
        "total": 5,
        "active_ready": [...],
        "active_pending": [...],
        "inactive": [...]
      },
      "gpu": {
        "status": "ok",
        "available": true,
        "name": "NVIDIA GeForce RTX 3090",
        "memory_gb": 24.0
      }
    },
    "timestamp": "2026-05-09T15:30:00Z"
  }
}
```

#### GET `/api/v1/health/summary`

Get health summary with issue counts.

**No authentication required**

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "overall_status": "healthy",
    "total_checks": 9,
    "ok_count": 8,
    "warning_count": 1,
    "error_count": 0
  }
}
```

---

### Dashboard APIs

#### GET `/api/v1/dashboard/stats`

Get dashboard statistics.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "llm_count": 5,
    "active_llm_count": 3,
    "ip_count": 10,
    "task_count": 75,
    "lora_count": 3,
    "version": "1.0.0",
    "status": "running"
  }
}
```

---

## API Versioning

Current API version: **v1**

All endpoints are prefixed with `/api/v1`. Future versions will use `/api/v2`, etc.

---

## Rate Limiting

Currently, rate limiting is not enforced. This may change in future versions.

---

## CORS Configuration

CORS is enabled for all origins in development. In production, configure allowed origins in `.env`:

```env
CORS_ORIGINS=["http://localhost:5173","https://yourdomain.com"]
```

---

## Interactive API Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These are automatically generated and always up-to-date.

---

## Migration Notes

### From Legacy Format

All APIs have been migrated to unified response format:

**Old Format:**
```json
{
  "id": 1,
  "name": "Example"
}
```

**New Format:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Example"
  },
  "message": "Operation successful"
}
```

### Frontend Access Pattern

```javascript
// Axios response interceptor passes through entire response
const { data } = await request.get('/api/v1/endpoint')

// Access data
const result = data.data  // Unified format
const message = data.message
```

---

## Support

For API issues or questions:
- GitHub Issues: https://github.com/yourusername/ip-creator/issues
- Documentation: README.md
