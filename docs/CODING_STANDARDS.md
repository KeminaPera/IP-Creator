# IP Creator 编码规范文档

**版本：** v1.0  
**创建日期：** 2026-05-28  
**适用范围：** 前后端所有代码  
**维护人：** 开发团队

---

## 📋 目录

- [一、前端开发规范](#一前端开发规范)
  - [1.1 组件抽取标准](#11-组件抽取标准)
  - [1.2 组件命名规范](#12-组件命名规范)
  - [1.3 Props 和 Emits 规范](#13-props-和-emits-规范)
  - [1.4 组合式 API 规范](#14-组合式-api-规范)
  - [1.5 状态管理规范](#15-状态管理规范)
- [二、前端样式规范](#二前端样式规范)
  - [2.1 BEM 命名规范](#21-bem-命名规范)
  - [2.2 全局样式使用指南](#22-全局样式使用指南)
  - [2.3 响应式设计规范](#23-响应式设计规范)
  - [2.4 Element Plus 使用规范](#24-element-plus-使用规范)
- [三、后端架构规范](#三后端架构规范)
  - [3.1 Router 职责划分](#31-router-职责划分)
  - [3.2 Service 层设计模式](#32-service-层设计模式)
  - [3.3 依赖注入规范](#33-依赖注入规范)
  - [3.4 异步编程规范](#34-异步编程规范)
- [四、API 接口规范](#四api-接口规范)
  - [4.1 统一响应格式](#41-统一响应格式)
  - [4.2 错误码规范](#42-错误码规范)
  - [4.3 分页规范](#43-分页规范)
  - [4.4 参数验证规范](#44-参数验证规范)
- [五、代码质量规范](#五代码质量规范)
  - [5.1 命名规范](#51-命名规范)
  - [5.2 注释规范](#52-注释规范)
  - [5.3 日志规范](#53-日志规范)
  - [5.4 测试规范](#54-测试规范)
- [六、Git 工作流规范](#六git-工作流规范)
  - [6.1 分支管理](#61-分支管理)
  - [6.2 提交信息规范](#62-提交信息规范)
  - [6.3 Code Review 流程](#63-code-review-流程)

---

## 一、前端开发规范

### 1.1 组件抽取标准

**原则：** 任何在 3 个以上页面中重复出现的 UI 模式，都应抽取为公共组件。

#### **已抽取的公共组件（必须复用）**

| 组件 | 路径 | 用途 | 使用场景 |
|------|------|------|---------|
| `StatusBadge` | `components/common/StatusBadge.vue` | 状态标签 | 所有状态展示 |
| `DataTable` | `components/common/DataTable.vue` | 数据表格 | 列表页面 |
| `ConfirmDialog` | `components/common/ConfirmDialog.vue` | 确认对话框 | 删除、确认操作 |
| `PageToolbar` | `components/common/PageToolbar.vue` | 页面工具栏 | 所有列表页顶部 |

#### **待抽取的公共组件（优先级 P0）**

| 组件 | 用途 | 涉及页面 | 优先级 |
|------|------|---------|--------|
| `CRUDDialog` | CRUD 表单对话框 | IPAssets、LLMManagement、LoRAModels | P0 |
| `StatCard` | 统计卡片 | Dashboard、DatasetManagement | P0 |
| `ImageUploader` | 图片上传组件 | IPAssets、DatasetManagement、IPAssetDetail | P0 |
| `ParamSlider` | 参数滑块 | Generate、IPAssets | P1 |
| `ParamInput` | 参数输入框 | Generate、IPAssets | P1 |
| `EmptyState` | 空状态展示 | 所有列表页 | P1 |

#### **组件抽取示例**

```vue
<!-- ✅ 正确：使用公共组件 -->
<template>
  <DataTable
    :data="items"
    :columns="columns"
    @edit="handleEdit"
    @delete="handleDelete"
  />
</template>

<script setup>
import DataTable from '@/components/common/DataTable.vue'
</script>

<!-- ❌ 错误：重复实现表格逻辑 -->
<template>
  <el-table :data="items">
    <el-table-column prop="name" label="名称" />
    <el-table-column label="操作">
      <el-button @click="handleEdit">编辑</el-button>
    </el-table-column>
  </el-table>
</template>
```

---

### 1.2 组件命名规范

#### **文件命名**
- ✅ PascalCase：`StatusBadge.vue`、`DataTable.vue`
- ❌ kebab-case：`status-badge.vue`、`data-table.vue`

#### **组件注册命名**
```javascript
// ✅ 正确：使用 PascalCase
import StatusBadge from '@/components/common/StatusBadge.vue'

// ✅ 正确：在模板中使用 PascalCase
<StatusBadge status="active" />

// ❌ 错误：使用 kebab-case
<status-badge status="active" />
```

#### **组件目录结构**
```
components/
├── common/              # 全局公共组件
│   ├── StatusBadge.vue
│   ├── DataTable.vue
│   ├── ConfirmDialog.vue
│   └── PageToolbar.vue
├── ip/                  # IP 资产相关组件
│   ├── IPFeatureManager.vue
│   └── MultiViewGallery.vue
├── lora/                # LoRA 训练相关组件
│   ├── TrainingWizard.vue
│   ├── TrainingMonitor.vue
│   └── QualityReport.vue
└── settings/            # 系统设置相关组件
    ├── LLMConfigForm.vue
    └── ModelSelector.vue
```

---

### 1.3 Props 和 Emits 规范

#### **Props 定义规范**

```javascript
// ✅ 正确：完整的 Props 定义
const props = defineProps({
  // 必填项
  loraId: {
    type: Number,
    required: true
  },
  
  // 带默认值的可选属性
  status: {
    type: String,
    default: 'pending',
    validator: (value) => ['pending', 'training', 'completed', 'failed'].includes(value)
  },
  
  // 对象类型必须提供工厂函数
  config: {
    type: Object,
    default: () => ({})
  },
  
  // 数组类型必须提供工厂函数
  items: {
    type: Array,
    default: () => []
  }
})

// ❌ 错误：简化的 Props 定义（缺少类型检查）
const props = defineProps(['loraId', 'status'])
```

#### **Emits 定义规范**

```javascript
// ✅ 正确：完整的 Emits 定义（TypeScript 风格）
const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'save', data: FormData): void
  (e: 'cancel'): void
  (e: 'delete', id: number): void
}>()

// 使用示例
emit('update:modelValue', false)
emit('save', formData)

// ❌ 错误：数组形式（缺少类型信息）
const emit = defineEmits(['update:modelValue', 'save', 'cancel'])
```

#### **双向绑定规范**

```javascript
// ✅ 正确：使用 computed 实现 v-model
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 模板中使用
<el-dialog v-model="visible" />
```

---

### 1.4 组合式 API 规范

#### **响应式数据声明**

```javascript
// ✅ 正确：基础类型使用 ref
const loading = ref(false)
const count = ref(0)
const name = ref('')

// ✅ 正确：对象类型使用 reactive
const form = reactive({
  name: '',
  description: '',
  status: 'active'
})

// ✅ 正确：数组使用 ref
const items = ref([])

// ❌ 错误：对象使用 ref（需要 .value 访问，不直观）
const form = ref({ name: '' })
form.value.name = 'test'  // 繁琐
```

#### **计算属性规范**

```javascript
// ✅ 正确：使用 computed 缓存计算结果
const isFormValid = computed(() => {
  return form.name && form.description
})

const filteredItems = computed(() => {
  return items.value.filter(item => item.status === 'active')
})

// ❌ 错误：在模板中直接计算（每次渲染都重新计算）
// <div v-if="items.filter(i => i.status === 'active').length > 0">
```

#### **Watch 使用规范**

```javascript
// ✅ 正确：监听单个 ref
watch(loading, (newVal) => {
  if (newVal) {
    console.log('Loading started')
  }
})

// ✅ 正确：监听多个 ref
watch([form.name, form.status], ([newName, newStatus]) => {
  console.log('Form changed:', newName, newStatus)
})

// ✅ 正确：监听 reactive 对象的属性
watch(
  () => form.status,
  (newStatus) => {
    if (newStatus === 'completed') {
      loadReport()
    }
  }
)

// ❌ 错误：深度监听整个 reactive 对象（性能差）
watch(form, (newVal) => { ... }, { deep: true })
```

#### **生命周期钩子规范**

```javascript
// ✅ 正确：在 setup 顶层调用
onMounted(() => {
  loadInitialData()
})

onUnmounted(() => {
  cleanupResources()
})

// ❌ 错误：在异步函数中调用生命周期
async function init() {
  onMounted(() => { ... })  // 错误！
}
```

---

### 1.5 状态管理规范

#### **组件内部状态**
- 仅在当前组件使用的状态，使用 `ref` 或 `reactive` 声明
- 多个组件共享的状态，考虑使用 Pinia

#### **Pinia Store 使用规范**

```javascript
// ✅ 正确：使用 Composition API 风格
export const useUserStore = defineStore('user', () => {
  // State
  const user = ref(null)
  const token = ref('')
  
  // Getters
  const isLoggedIn = computed(() => !!token.value)
  
  // Actions
  async function login(credentials) {
    const response = await api.login(credentials)
    token.value = response.token
    user.value = response.user
  }
  
  function logout() {
    token.value = ''
    user.value = null
  }
  
  return { user, token, isLoggedIn, login, logout }
})
```

---

## 二、前端样式规范

### 2.1 BEM 命名规范

**格式：** `.block__element--modifier`

```css
/* ✅ 正确：BEM 命名 */
.training-monitor {              /* Block */
  padding: 20px;
}

.training-monitor__header {      /* Element */
  display: flex;
  justify-content: space-between;
}

.training-monitor__title {       /* Element */
  font-size: 20px;
  font-weight: 600;
}

.training-monitor__status--success {  /* Modifier */
  color: #67c23a;
}

.training-monitor__status--error {    /* Modifier */
  color: #f56c6c;
}

/* ❌ 错误：嵌套过深 */
.training-monitor .header .title .status {
  color: red;
}
```

#### **命名约定**

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| Block | 独立组件 | `.card`, `.modal`, `.navbar` |
| Element | 使用 `__` 连接 | `.card__title`, `.modal__header` |
| Modifier | 使用 `--` 连接 | `.button--primary`, `.card--large` |

---

### 2.2 全局样式使用指南

**必须使用全局样式类的场景：**

```vue
<!-- ✅ 正确：使用全局样式类 -->
<template>
  <div class="page-container">
    <h1 class="page-title">IP 资产管理</h1>
    
    <div class="flex-between page-toolbar">
      <el-button type="primary">新增</el-button>
    </div>
    
    <div class="empty-hint" v-if="items.length === 0">
      暂无数据
    </div>
  </div>
</template>

<style scoped>
/* ❌ 错误：重复定义全局已有的样式 */
/*
.page-container {
  padding: 20px;  // 已在 common.css 中定义
}
*/
</style>
```

#### **全局样式类清单**

| 类别 | 样式类 | 用途 |
|------|--------|------|
| 布局 | `.page-container` | 页面容器 |
| 布局 | `.page-toolbar` | 工具栏间距 |
| 布局 | `.stats-row` | 统计行间距 |
| 文本 | `.page-title` | 页面标题 |
| 文本 | `.text-muted` | 弱化文本 |
| 文本 | `.text-center` | 居中文本 |
| Flex | `.flex-center` | 垂直居中 |
| Flex | `.flex-between` | 两端对齐 |
| 对话框 | `.dialog-actions` | 对话框操作区 |
| 表单 | `.form-hint` | 表单提示 |
| 空状态 | `.empty-hint` | 空状态展示 |
| 加载 | `.loading-container` | 加载容器 |

---

### 2.3 响应式设计规范

#### **断点定义**

```css
/* 移动设备 (< 768px) */
@media (max-width: 768px) {
  .grid-responsive {
    grid-template-columns: 1fr;
  }
}

/* 平板设备 (768px - 1024px) */
@media (min-width: 768px) and (max-width: 1024px) {
  .grid-responsive {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 桌面设备 (> 1024px) */
@media (min-width: 1024px) {
  .grid-responsive {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

#### **响应式布局示例**

```vue
<template>
  <!-- ✅ 正确：使用 Element Plus 响应式栅格 -->
  <el-row :gutter="16">
    <el-col :xs="24" :sm="12" :md="8" :lg="6">
      <StatCard title="IP 资产" :value="ipCount" />
    </el-col>
  </el-row>
</template>
```

---

### 2.4 Element Plus 使用规范

#### **统一按钮样式**

```vue
<!-- ✅ 正确：统一按钮顺序和类型 -->
<template>
  <div class="dialog-actions">
    <el-button @click="handleCancel">取消</el-button>
    <el-button type="primary" @click="handleConfirm">
      确定
    </el-button>
  </div>
</template>

<!-- ❌ 错误：按钮顺序混乱 -->
<el-button type="primary">确定</el-button>
<el-button>取消</el-button>
```

#### **统一表单布局**

```vue
<!-- ✅ 正确：统一表单布局 -->
<el-form :model="form" label-width="120px" size="default">
  <el-form-item label="名称">
    <el-input v-model="form.name" />
  </el-form-item>
</el-form>

<!-- ❌ 错误：混用不同的 label-width -->
<el-form :model="form" label-width="100px">
  <el-form-item label-width="120px" label="名称">
```

#### **统一表格操作列**

```vue
<!-- ✅ 正确：操作列右对齐，统一按钮顺序 -->
<el-table-column label="操作" width="200" align="right">
  <template #default="{ row }">
    <el-button size="small" @click="handleEdit(row)">编辑</el-button>
    <el-button size="small" type="danger" @click="handleDelete(row)">
      删除
    </el-button>
  </template>
</el-table-column>
```

---

## 三、后端架构规范

### 3.1 Router 职责划分

**原则：** Router 只负责接收请求、调用 Service、返回响应，不包含业务逻辑。

#### **Router 结构规范**

```python
# ✅ 正确：Router 只负责请求处理
@router.post("/{lora_id}/train")
async def start_training(
    lora_id: int,
    config: TrainingConfigRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """启动 LoRA 训练任务"""
    # 1. 参数验证（由 Pydantic 自动完成）
    # 2. 调用 Service 层
    service = LoRAService(db)
    task = await service.start_training(lora_id, config)
    
    # 3. 返回统一响应
    return success_response(
        data={"task_id": task.id},
        message="Training task started"
    )

# ❌ 错误：Router 包含业务逻辑
@router.post("/{lora_id}/train")
async def start_training(lora_id: int):
    # 直接操作数据库
    lora_model = await db.get(LoRAModel, lora_id)
    if not lora_model:
        raise NotFoundException(...)
    
    # 直接调用 Celery
    task = train_lora_task.delay(lora_id)
    
    # 直接更新数据库
    lora_model.task_id = task.id
    await db.commit()
```

#### **Router 文件命名规范**

| 文件 | 职责 | 路径前缀 |
|------|------|---------|
| `ip_router.py` | IP 资产管理 | `/api/v1/ip` |
| `lora_router.py` | LoRA 训练管理 | `/api/v1/lora` |
| `generation_router.py` | 内容生成 | `/api/v1/generation` |
| `dataset_router.py` | 数据集管理 | `/api/v1/datasets` |
| `llm_router.py` | LLM 通道管理 | `/api/v1/llm` |
| `task_router.py` | 任务监控 | `/api/v1/tasks` |

---

### 3.2 Service 层设计模式

#### **BaseService 抽象基类**

```python
# app/services/base_service.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Type
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')

class BaseService(ABC, Generic[T]):
    """Service 层抽象基类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @abstractmethod
    async def get_by_id(self, id: int) -> T | None:
        """根据 ID 获取资源"""
        pass
    
    @abstractmethod
    async def list(self, page: int = 1, page_size: int = 20) -> tuple[list[T], int]:
        """获取资源列表（分页）"""
        pass
    
    @abstractmethod
    async def create(self, data: dict) -> T:
        """创建资源"""
        pass
    
    @abstractmethod
    async def update(self, id: int, data: dict) -> T:
        """更新资源"""
        pass
    
    @abstractmethod
    async def delete(self, id: int) -> bool:
        """删除资源"""
        pass
```

#### **具体 Service 实现**

```python
# app/services/lora_service.py
from app.services.base_service import BaseService
from app.models.lora_model import LoRAModel

class LoRAService(BaseService[LoRAModel]):
    """LoRA 训练服务"""
    
    async def get_by_id(self, id: int) -> LoRAModel | None:
        from sqlalchemy import select
        result = await self.db.execute(
            select(LoRAModel).where(LoRAModel.id == id)
        )
        return result.scalar_one_or_none()
    
    async def start_training(self, lora_id: int, config: dict) -> dict:
        """启动训练（业务逻辑）"""
        # 1. 验证模型存在
        lora_model = await self.get_by_id(lora_id)
        if not lora_model:
            raise NotFoundException(resource="LoRAModel", identifier=str(lora_id))
        
        # 2. 验证数据集
        if not lora_model.dataset_id:
            raise BadRequestException("Dataset not associated")
        
        # 3. 启动 Celery 任务
        from celery_worker import train_lora_task
        task = train_lora_task.delay(lora_id, config)
        
        # 4. 更新状态
        lora_model.status = 'training'
        lora_model.task_id = task.id
        await self.db.commit()
        
        return {"task_id": task.id}
```

#### **设计模式应用**

**1. 工厂模式**

```python
# app/services/adapter_factory.py
from app.services.adapters.base import BaseAdapter
from app.services.adapters.image_adapter import ImageAdapter
from app.services.adapters.text_adapter import TextAdapter

class AdapterFactory:
    """适配器工厂"""
    
    _adapters = {
        'image': ImageAdapter,
        'text': TextAdapter,
    }
    
    @classmethod
    def create(cls, adapter_type: str) -> BaseAdapter:
        """创建适配器实例"""
        adapter_class = cls._adapters.get(adapter_type)
        if not adapter_class:
            raise ValueError(f"Unknown adapter type: {adapter_type}")
        return adapter_class()
```

**2. 策略模式**

```python
# app/services/training_strategy.py
from abc import ABC, abstractmethod

class TrainingStrategy(ABC):
    """训练策略接口"""
    
    @abstractmethod
    def generate_config(self, dataset_size: int) -> dict:
        pass

class QuickTestStrategy(TrainingStrategy):
    """快速测试策略"""
    
    def generate_config(self, dataset_size: int) -> dict:
        return {
            "max_train_steps": 100,
            "learning_rate": 1e-3,
            "train_batch_size": 1
        }

class HighQualityStrategy(TrainingStrategy):
    """高质量训练策略"""
    
    def generate_config(self, dataset_size: int) -> dict:
        return {
            "max_train_steps": 1000,
            "learning_rate": 1e-4,
            "train_batch_size": 4
        }
```

---

### 3.3 依赖注入规范

```python
# ✅ 正确：使用 FastAPI 依赖注入
@router.get("/{lora_id}")
async def get_lora(
    lora_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    service = LoRAService(db)
    lora = await service.get_by_id(lora_id)
    return success_response(data=lora)

# ❌ 错误：手动创建依赖
@router.get("/{lora_id}")
async def get_lora(lora_id: int):
    db = AsyncSessionLocal()
    current_user = get_user_from_token()
```

---

### 3.4 异步编程规范

#### **Async/Await 使用规范**

```python
# ✅ 正确：使用 async/await
async def process_training(lora_id: int):
    # 异步数据库操作
    lora = await db.get(LoRAModel, lora_id)
    
    # 异步文件操作
    async with aiofiles.open(log_path, 'w') as f:
        await f.write(log_content)
    
    # 异步 HTTP 请求
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)

# ❌ 错误：在 async 函数中使用同步阻塞操作
async def process_training(lora_id: int):
    lora = db.get(LoRAModel, lora_id)  # 阻塞！
    
    with open(log_path, 'w') as f:  # 阻塞！
        f.write(log_content)
```

#### **并发任务处理**

```python
# ✅ 正确：使用 asyncio.gather 并发执行
async def generate_test_images(lora_id: int, count: int = 5):
    tasks = [
        generate_single_image(lora_id, prompt)
        for prompt in test_prompts[:count]
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理结果
    success_results = [r for r in results if not isinstance(r, Exception)]

# ❌ 错误：串行执行
async def generate_test_images(lora_id: int, count: int = 5):
    results = []
    for prompt in test_prompts[:count]:
        result = await generate_single_image(lora_id, prompt)
        results.append(result)
```

---

## 四、API 接口规范

### 4.1 统一响应格式

**所有 API 响应必须遵循以下格式：**

#### **成功响应**

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功",  // 可选
  "pagination": {          // 可选，仅列表接口
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

#### **错误响应**

```json
{
  "success": false,
  "error": {
    "error": "NotFoundError",
    "message": "Resource with ID '123' not found",
    "code": "RESOURCE_NOT_FOUND",
    "details": null,
    "request_id": "req_abc123"
  }
}
```

#### **使用统一响应函数**

```python
# ✅ 正确：使用 response.py 中的函数
from app.utils.response import success_response, created_response, deleted_response

# 创建资源
return created_response(data=new_item, message="Created successfully")

# 更新资源
return success_response(data=updated_item, message="Updated successfully")

# 删除资源
return deleted_response(resource_id=item_id, message="Deleted successfully")

# 列表查询
return list_response(
    items=items,
    page=page,
    page_size=page_size,
    total=total
)

# ❌ 错误：直接返回字典
return {"success": True, "data": item}
```

---

### 4.2 错误码规范

#### **错误码命名规则**

格式：`{RESOURCE}_{ERROR_TYPE}`

```python
# ✅ 正确：统一的错误码
"IP_ASSET_NOT_FOUND"
"LORA_MODEL_CONFLICT"
"DATASET_VALIDATION_ERROR"

# ❌ 错误：不规范的错误码
"NOT_FOUND"
"ERROR_001"
```

#### **HTTP 状态码映射**

| 状态码 | 异常类 | 使用场景 |
|--------|--------|---------|
| 400 | `BadRequestException` | 请求参数错误 |
| 401 | `UnauthorizedException` | 未认证 |
| 403 | `ForbiddenException` | 无权限 |
| 404 | `NotFoundException` | 资源不存在 |
| 409 | `ConflictException` | 资源冲突 |
| 422 | `ValidationException` | 验证失败 |
| 429 | `RateLimitException` | 频率限制 |
| 500 | `AppException` | 服务器内部错误 |

#### **异常使用示例**

```python
# ✅ 正确：使用统一的异常类
from app.core.exceptions import NotFoundException, BadRequestException

async def get_ip_asset(ip_id: int):
    ip_asset = await db.get(IPAsset, ip_id)
    if not ip_asset:
        raise NotFoundException(resource="IPAsset", identifier=str(ip_id))
    return ip_asset

async def create_ip_asset(data: dict):
    # 验证触发词唯一性
    existing = await check_trigger_word(data['trigger_word'])
    if existing:
        raise ConflictException(
            message=f"Trigger word '{data['trigger_word']}' already exists",
            code="TRIGGER_WORD_CONFLICT"
        )

# ❌ 错误：直接抛出 HTTPException
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="Not found")
```

---

### 4.3 分页规范

#### **查询参数**

```
GET /api/v1/ip-assets?page=1&page_size=20&sort=created_at&order=desc
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码（从 1 开始） |
| `page_size` | int | 20 | 每页数量（最大 100） |
| `sort` | string | created_at | 排序字段 |
| `order` | string | desc | 排序方向（asc/desc） |

#### **响应格式**

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

#### **分页实现示例**

```python
# ✅ 正确：使用 list_response
@router.get("/ip-assets")
async def list_ip_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
):
    # 查询数据
    query = select(IPAsset)
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()
    
    result = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    items = result.scalars().all()
    
    # 返回统一响应
    return list_response(
        items=items,
        page=page,
        page_size=page_size,
        total=total
    )
```

---

### 4.4 参数验证规范

#### **Pydantic Schema 验证**

```python
# app/schemas/lora_schema.py
from pydantic import BaseModel, Field, validator

class LoRACreateRequest(BaseModel):
    """LoRA 创建请求"""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="LoRA 模型名称"
    )
    
    base_model: str = Field(
        ...,
        description="基础模型路径"
    )
    
    training_params: dict = Field(
        default_factory=dict,
        description="训练参数"
    )
    
    @validator('name')
    def validate_name(cls, v):
        """验证名称格式"""
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
```

#### **Router 中使用 Schema**

```python
# ✅ 正确：使用 Pydantic Schema 自动验证
@router.post("/lora")
async def create_lora(
    request: LoRACreateRequest,  # 自动验证
    db: AsyncSession = Depends(get_db_session),
):
    service = LoRAService(db)
    lora = await service.create(request.dict())
    return created_response(data=lora)
```

---

## 五、代码质量规范

### 5.1 命名规范

#### **Python 命名规范**

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块/包 | snake_case | `lora_service.py` |
| 类名 | PascalCase | `LoRAService`, `QualityAssessor` |
| 函数/方法 | snake_case | `generate_image()`, `start_training()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_BATCH_SIZE`, `DEFAULT_LR` |
| 私有方法 | `_leading_underscore` | `_validate_params()` |
| 变量 | snake_case | `lora_model`, `task_id` |

#### **Vue/JavaScript 命名规范**

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件文件 | PascalCase.vue | `StatusBadge.vue` |
| 组件标签 | PascalCase | `<StatusBadge />` |
| 变量/函数 | camelCase | `loading`, `handleClick()` |
| 常量 | UPPER_SNAKE_CASE | `API_BASE_URL` |
| 私有变量 | `_leadingUnderscore` | `_internalState` |

---

### 5.2 注释规范

#### **Python 文档字符串**

```python
async def generate_test_images(
    lora_id: int,
    num_images: int = 5,
    prompts: list[str] | None = None
) -> list[dict]:
    """
    生成测试图片用于质量评估。
    
    Args:
        lora_id: LoRA 模型 ID
        num_images: 生成图片数量（默认 5）
        prompts: 自定义提示词列表（可选）
    
    Returns:
        生成的图片信息列表，包含路径和评分
    
    Raises:
        NotFoundException: LoRA 模型不存在
        BadRequestException: 参数验证失败
    
    Example:
        >>> images = await generate_test_images(lora_id=123, num_images=5)
        >>> print(images[0]['path'])
        '/data/test_images/img_001.png'
    """
    pass
```

#### **Vue 组件注释**

```javascript
/**
 * 训练监控组件
 * 
 * 功能：
 * - 实时显示训练进度
 * - 展示 Loss/LR 曲线
 * - 查看训练日志
 * 
 * @module TrainingMonitor
 * @requires echarts
 * @requires ElementPlus
 */
```

---

### 5.3 日志规范

#### **日志级别使用**

```python
from app.utils.logger import logger

# DEBUG：详细调试信息（仅开发环境）
logger.debug(f"Processing image: {image_path}")

# INFO：正常业务流程
logger.info(f"Training started for LoRA {lora_id}")

# WARNING：潜在问题，但不影响运行
logger.warning(f"GPU memory low: {memory_mb}MB remaining")

# ERROR：错误但不影响服务继续运行
logger.error(f"Failed to generate image: {error}")

# CRITICAL：严重错误，服务可能无法继续
logger.critical(f"Database connection lost: {error}")
```

#### **日志格式规范**

```python
# ✅ 正确：包含上下文信息
logger.info(f"Training completed: lora_id={lora_id}, epochs={epochs}, loss={loss:.4f}")

# ❌ 错误：缺少上下文
logger.info("Training completed")
```

---

### 5.4 测试规范

#### **单元测试命名**

```python
# tests/test_lora_service.py
class TestLoRAService:
    """LoRA 服务测试"""
    
    async def test_create_lora_success(self):
        """测试创建 LoRA 成功"""
        pass
    
    async def test_create_lora_duplicate_trigger_word(self):
        """测试重复触发词应抛出冲突异常"""
        pass
    
    async def test_start_training_without_dataset(self):
        """测试未关联数据集时启动训练应失败"""
        pass
```

#### **测试覆盖率要求**

| 模块类型 | 最低覆盖率 | 说明 |
|---------|-----------|------|
| Service 层 | 80% | 核心业务逻辑 |
| Router 层 | 60% | 请求处理 |
| Utils 工具函数 | 90% | 纯函数 |

---

## 六、Git 工作流规范

### 6.1 分支管理

#### **分支命名规范**

| 分支类型 | 命名格式 | 示例 |
|---------|---------|------|
| 主分支 | `main` | 生产环境代码 |
| 开发分支 | `develop` | 集成测试代码 |
| 功能分支 | `feature/{description}` | `feature/ip-adapter` |
| 修复分支 | `fix/{description}` | `fix/training-error` |
| 优化分支 | `optimization/{description}` | `optimization/websocket` |

#### **分支工作流**

```
main (生产)
  ↑
  | 合并
develop (开发)
  ↑
  | 合并
feature/xxx (功能开发)
```

---

### 6.2 提交信息规范

#### **格式**

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### **Type 类型**

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: add WebSocket training monitor` |
| `fix` | Bug 修复 | `fix: resolve training task deadlock` |
| `docs` | 文档更新 | `docs: update API documentation` |
| `style` | 代码格式 | `style: format code with black` |
| `refactor` | 重构 | `refactor: extract BaseService class` |
| `test` | 测试 | `test: add unit tests for LoRAService` |
| `chore` | 构建/工具 | `chore: update dependencies` |

#### **提交示例**

```bash
feat(lora): add automatic quality assessment after training

- Trigger quality assessment when training completes
- Generate 5 test images with CLIP similarity scoring
- Add training diagnosis report (overfitting/underfitting)

Closes #123
```

---

### 6.3 Code Review 流程

#### **提交 PR 前检查清单**

- [ ] 代码通过 lint 检查
- [ ] 单元测试通过率 >= 80%
- [ ] 更新相关文档
- [ ] 提交信息符合规范
- [ ] 无调试代码（console.log、print）
- [ ] 无敏感信息（密码、密钥）

#### **Code Review 要点**

1. **功能正确性**：是否实现需求
2. **代码质量**：是否遵循编码规范
3. **性能影响**：是否有性能问题
4. **安全性**：是否有安全漏洞
5. **可维护性**：是否易于理解和修改

---

## 附录

### A. 快速参考卡片

#### **前端组件创建检查清单**

- [ ] 组件命名 PascalCase
- [ ] Props 完整定义（类型、默认值、验证）
- [ ] Emits 使用 TypeScript 风格
- [ ] 使用全局样式类（如有）
- [ ] 响应式数据使用 ref/reactive
- [ ] 添加组件注释

#### **后端 API 创建检查清单**

- [ ] Router 只负责请求处理
- [ ] 业务逻辑在 Service 层
- [ ] 使用统一响应函数
- [ ] 使用统一异常类
- [ ] Pydantic Schema 验证参数
- [ ] 添加文档字符串
- [ ] 添加日志记录

---

### B. 常用命令

```bash
# 前端
npm run lint              # 代码检查
npm run format            # 格式化代码
npm run test              # 运行测试

# 后端
black app/                # 格式化 Python 代码
flake8 app/               # 代码检查
pytest tests/             # 运行测试
pytest --cov=app tests/   # 测试覆盖率

# Git
git commit -m "feat: ..." # 提交代码
git push origin feature/xxx  # 推送分支
```

---

**文档版本历史：**

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| v1.0 | 2026-05-28 | 初始版本 | AI Assistant |

---

**本规范自创建之日起生效，所有新代码必须遵循本规范。现有代码逐步重构以符合规范。**
