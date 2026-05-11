# LoRA 角色训练功能详细设计 - v2.0

**文档版本：** v2.0  
**创建日期：** 2026-05-10  
**更新日期：** 2026-05-10  
**状态：** 📝 讨论中 - 待打磨

**本次更新重点：**
- ✅ 详细设计批量图片标注流程
- ✅ Caption 生成：固定模板 + 人工修改
- ⏸️ AI 生成（后续版本实现）
- ⏸️ 训练失败处理（后续讨论）

**已确认决策：**
- ✅ Caption 模板：固定模板（不使用用户自定义）
- ✅ AI 生成：暂不实现，后续版本决定使用哪个模型
- ✅ 标注必填项：角度必填，其他可选

---

## 🎯 一、功能定位

为个人 IP 打造提供**专属角色 LoRA 训练**能力，核心流程：
```
上传图片 → 批量标注 → 生成Caption → 训练LoRA → 质量评估 → 使用生成
```

---

## 📊 二、核心功能：批量图片标注与 Caption 生成

### **2.1 为什么需要标注和 Caption？**

**标注信息**用于生成 **Caption 文件**（.txt），告诉 AI 每张图片的内容。

**对比：**

| 训练方式 | 角色一致性 | 场景泛化能力 | 总体质量 |
|---------|-----------|------------|---------|
| ❌ 无 Caption | 60% | 20% | ⭐⭐ |
| ✅ 有 Caption | 90% | 85% | ⭐⭐⭐⭐⭐ |

**原因：**
- 有 Caption：AI 知道哪些是角色特征，哪些是场景/姿势
- 无 Caption：AI 把所有内容都当成角色特征，无法泛化

---

### **2.2 完整工作流程**

```
┌─────────────────────────────────────────────────────┐
│  步骤 1: 上传图片                                      │
│  - 批量选择（最多 50 张）                              │
│  - 拖拽上传                                           │
│  - 自动检测格式和质量                                  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  步骤 2: 批量标注                                      │
│  - 设置全局默认值（角度/表情/姿势/背景）                │
│  - 一键应用到所有图片                                  │
│  - 可逐个修改                                         │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  步骤 3: 生成 Caption                                 │
│  - 方式一：模板生成（推荐）                            │
│  - 方式二：AI 生成（可选）                             │
│  - 预览生成结果                                       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  步骤 4: 人工审核和修改                                │
│  - 逐张浏览图片 + Caption                             │
│  - 直接编辑文本                                       │
│  - 修改标注自动更新 Caption                           │
│  - 批量操作（复制/应用）                               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  步骤 5: 确认提交                                      │
│  - 保存到数据库                                       │
│  - 生成 .txt 文件                                     │
│  - 准备训练                                           │
└─────────────────────────────────────────────────────┘
```

---

### **2.3 标注信息定义**

| 字段 | 必填 | 选项 | 说明 |
|------|------|------|------|
| **角度 (Angle)** | ✅ | front / side / back | 视角方向 |
| **表情 (Expression)** | ⭕ | neutral / happy / sad / angry / surprised | 角色表情 |
| **姿势 (Pose)** | ⭕ | standing / sitting / running / jumping | 动作姿态 |
| **背景 (Background)** | ⭕ | white / indoor / outdoor / nature | 背景类型 |
| **质量评分** | ❌ | 0-100 | 自动计算，可手动调整 |

---

### **2.4 批量标注 UI 设计**

#### **界面布局**

```
┌──────────────────────────────────────────────────────────────┐
│  📝 批量标注图片                          已上传 25 张图片     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐      │
│  │  🔧 批量设置（应用到所有图片）                        │      │
│  │                                                    │      │
│  │  角度：[front ▼]  表情：[neutral ▼]                 │      │
│  │  姿势：[standing ▼]  背景：[white ▼]                │      │
│  │                                                    │      │
│  │  [应用到所有图片]                                    │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  ┌────────────────────────────────────────────────────┐      │
│  │  📸 图片网格（可逐个修改）                            │      │
│  │                                                    │      │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │      │
│  │  │ [图片1] │ │ [图片2] │ │ [图片3] │ │ [图片4] │  │      │
│  │  │ 正面    │ │ 正面    │ │ 侧面    │ │ 侧面    │  │      │
│  │  │ [修改]  │ │ [修改]  │ │ [修改]  │ │ [修改]  │  │      │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │      │
│  │                                                    │      │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │      │
│  │  │ [图片5] │ │ [图片6] │ │ [图片7] │ │ [图片8] │  │      │
│  │  │ 背面    │ │ 背面    │ │ ...     │ │ ...     │  │      │
│  │  │ [修改]  │ │ [修改]  │ │ [修改]  │ │ [修改]  │  │      │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  [取消] [生成 Caption] →                                     │
└──────────────────────────────────────────────────────────────┘
```

#### **单个修改弹窗**

```
┌──────────────────────────────────────────┐
│  ✏️ 修改图片标注                           │
│                                          │
│  [图片预览]                               │
│                                          │
│  角度：[front ▼]                          │
│  表情：[neutral ▼]                        │
│  姿势：[standing ▼]                       │
│  背景：[white ▼]                          │
│                                          │
│  生成的 Caption 预览：                     │
│  ┌────────────────────────────────────┐  │
│  │ xiao_huli, front view, standing,   │  │
│  │ white background                   │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [取消] [保存]                            │
└──────────────────────────────────────────┘
```

---

### **2.5 Caption 生成策略（固定模板）**

**MVP 方案：固定模板生成**

**固定模板格式：**
```
{trigger_word}, {angle} view, {pose}, {background}
```

**说明：**
- 模板固定，用户不可自定义
- 保证 Caption 格式一致性
- 降低用户学习成本

**变量映射表：**

| 变量 | 标注值 | 转换结果 | 必填 |
|------|--------|---------|------|
| `{trigger_word}` | 用户设置 | xiao_huli_character | ✅ |
| `{angle}` | front | front view | ✅ |
| | side | side view | |
| | back | back view | |
| `{pose}` | standing | standing | ⭕ |
| | sitting | sitting | |
| | running | running | |
| | jumping | jumping | |
| `{background}` | white | white background | ⭕ |
| | indoor | indoor | |
| | outdoor | outdoor | |
| | nature | nature background | |

**注意：**
- 表情（expression）不包含在模板中（保持简洁）
- pose 和 background 如果未填写，则自动省略

**生成示例：**

**示例 1：完整标注**
```
输入：
  触发词: xiao_huli_character
  角度: front
  姿势: standing
  背景: white

输出：
  xiao_huli_character, front view, standing, white background
```

**示例 2：省略可选字段**
```
输入：
  触发词: xiao_huli_character
  角度: side
  姿势: (未填写)
  背景: (未填写)

输出：
  xiao_huli_character, side view
```

**后端实现：**
```python
def generate_caption_from_template(annotation: dict, trigger_word: str) -> str:
    """
    根据固定模板生成 Caption
    
    Args:
        annotation: 标注信息 {angle, pose, background}
        trigger_word: 触发词
    
    Returns:
        Caption 文本
    """
    parts = [trigger_word]
    
    # 角度（必填）
    angle_map = {
        'front': 'front view',
        'side': 'side view',
        'back': 'back view'
    }
    if annotation.get('angle'):
        parts.append(angle_map.get(annotation['angle'], ''))
    
    # 姿势（可选）
    if annotation.get('pose'):
        parts.append(annotation['pose'])
    
    # 背景（可选）
    bg_map = {
        'white': 'white background',
        'indoor': 'indoor',
        'outdoor': 'outdoor',
        'nature': 'nature background'
    }
    if annotation.get('background'):
        parts.append(bg_map.get(annotation['background'], ''))
    
    # 过滤空值并拼接
    return ', '.join([p for p in parts if p])
```

---

#### **~~策略二：AI 生成~~（后续版本）**

**状态：** ⏸️ 暂不实现

**计划：**
- v2.0 版本评估是否添加
- 根据用户需求决定是否接入
- 候选模型：GPT-4V / Qwen-VL / BLIP

**如果后续添加，实现方式：**
- 作为“增强功能”可选开启
- AI 生成后仍需人工审核
- 生成格式仍需符合固定模板规范

---

### **2.6 Caption 编辑和确认（核心交互）**

#### **编辑界面**

```
┌────────────────────────────────────────────────────────┐
│  ✏️ 编辑 Caption                    3 / 25              │
│                                                        │
│  [◀ 上一张]                              [下一张 ▶]     │
│                                                        │
│  ┌──────────────────────┐  ┌──────────────────────┐   │
│  │                      │  │ 当前 Caption：        │   │
│  │                      │  │ ┌──────────────────┐ │   │
│  │    [图片预览]        │  │ │xiao_huli, front  │ │   │
│  │                      │  │ │view, standing,   │ │   │
│  │                      │  │ │white background  │ │   │
│  │                      │  │ └──────────────────┘ │   │
│  │                      │  │                      │   │
│  │                      │  │ [可直接编辑文本]      │   │
│  │                      │  │                      │   │
│  └──────────────────────┘  │ 标注信息：            │   │
│                            │ 角度：[front ▼]       │   │
│                            │ 表情：[neutral ▼]     │   │
│                            │ 姿势：[standing ▼]    │   │
│                            │ 背景：[white ▼]       │   │
│                            └──────────────────────┘   │
│                                                        │
│  快速操作：                                             │
│  [复制上一张] [应用到全部] [重新生成]                    │
│                                                        │
│  [保存并继续]                                           │
└────────────────────────────────────────────────────────┘
```

#### **交互说明**

**1. 逐张浏览**
- 左右箭头切换图片
- 显示当前进度（3/25）

**2. 两种编辑方式**
- **直接编辑文本**：修改 Caption 文本框
- **修改标注字段**：自动更新 Caption

**3. 批量操作**
- **复制上一张**：将上一张的标注和 Caption 复制到当前
- **应用到全部**：将当前标注应用到所有未修改的图片
- **重新生成**：使用模板重新生成当前图片的 Caption

**4. 保存逻辑**
- 点击"保存并继续"：
  - 保存到数据库
  - 自动生成 .txt 文件
  - 进入下一张

---

### **2.7 数据结构设计**

#### **数据库表：dataset_images**

```sql
CREATE TABLE dataset_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    
    -- 文件信息
    file_path VARCHAR(500) NOT NULL,
    width INTEGER,
    height INTEGER,
    file_size_kb FLOAT,
    
    -- 标注信息
    angle VARCHAR(20),           -- front/side/back
    expression VARCHAR(50),      -- neutral/happy/sad/angry/surprised
    pose VARCHAR(50),            -- standing/sitting/running/jumping
    background VARCHAR(50),      -- white/indoor/outdoor/nature
    quality_score FLOAT,         -- 0-100
    
    -- Caption
    caption TEXT,                -- 生成的 Caption
    caption_method VARCHAR(20),  -- template/ai/manual
    
    -- 训练相关
    is_selected BOOLEAN DEFAULT TRUE,    -- 是否用于训练
    is_augmented BOOLEAN DEFAULT FALSE,  -- 是否增强图片
    parent_image_id INTEGER,             -- 原图 ID（如果是增强）
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (dataset_id) REFERENCES training_datasets(id) ON DELETE CASCADE
);

CREATE INDEX idx_dataset_images_dataset ON dataset_images(dataset_id);
CREATE INDEX idx_dataset_images_angle ON dataset_images(angle);
```

---

### **2.8 API 接口设计**

#### **1. 批量上传图片**

```
POST /api/v1/datasets/{dataset_id}/upload-images
Content-Type: multipart/form-data

参数：
- files: List[UploadFile]  # 图片文件
- angle: str (optional)    # 批量标注角度
- expression: str (optional)
- pose: str (optional)
- background: str (optional)

响应：
{
  "success": true,
  "data": {
    "uploaded_count": 25,
    "failed_count": 0,
    "duplicate_count": 0,
    "images": [
      {
        "id": 1,
        "file_path": "/path/to/image.jpg",
        "angle": "front",
        "caption": null
      }
    ]
  }
}
```

#### **2. 批量生成 Caption**

```
POST /api/v1/datasets/{dataset_id}/generate-captions

参数：
{
  "trigger_word": "xiao_huli_character",  // 必填
  "image_ids": [1, 2, 3]  // 可选，不传则处理所有
}

响应：
{
  "success": true,
  "data": {
    "processed": 25,
    "failed": 0
  }
}
```

#### **3. 更新单张图片标注**

```
PATCH /api/v1/datasets/{dataset_id}/images/{image_id}

参数：
{
  "angle": "front",
  "expression": "happy",
  "pose": "standing",
  "background": "white",
  "caption": "xiao_huli, front view, standing, white background, happy expression"
}

响应：
{
  "success": true,
  "data": {
    "id": 1,
    "caption": "xiao_huli, front view..."
  }
}
```

#### **4. 获取图片列表**

```
GET /api/v1/datasets/{dataset_id}/images?skip=0&limit=20

响应：
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "file_path": "/path/to/image.jpg",
        "angle": "front",
        "expression": "neutral",
        "pose": "standing",
        "background": "white",
        "caption": "xiao_huli, front view, standing, white background"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 25
    }
  }
}
```

---

### **2.9 前端实现要点**

#### **状态管理**

```javascript
const annotationState = reactive({
  images: [],  // 所有图片及其标注
  batchSettings: {
    angle: null,
    expression: null,
    pose: null,
    background: null
  },
  currentIndex: 0,  // 当前编辑的图片索引
  triggerWord: ''
})

// 图片对象结构
{
  id: 1,
  file: File对象,
  preview: 'blob:url...',
  annotation: {
    angle: 'front',
    expression: 'neutral',
    pose: 'standing',
    background: 'white'
  },
  caption: 'xiao_huli, front view, standing, white background',
  modified: false  // 是否被用户修改过
}
```

#### **批量应用逻辑**

```javascript
function applyBatchToAll() {
  annotationState.images.forEach(img => {
    // 只应用到未手动修改的图片
    if (!img.modified) {
      if (annotationState.batchSettings.angle) {
        img.annotation.angle = annotationState.batchSettings.angle
      }
      if (annotationState.batchSettings.expression) {
        img.annotation.expression = annotationState.batchSettings.expression
      }
      // ... 其他字段
      
      // 重新生成 Caption
      img.caption = generateCaptionFromTemplate(
        img.annotation,
        annotationState.triggerWord
      )
    }
  })
}
```

#### **Caption 自动生成**

```javascript
function generateCaptionFromTemplate(annotation, triggerWord) {
  const parts = [triggerWord]
  
  const angleMap = {
    front: 'front view',
    side: 'side view',
    back: 'back view'
  }
  
  if (annotation.angle) parts.push(angleMap[annotation.angle])
  if (annotation.pose) parts.push(annotation.pose)
  
  const bgMap = {
    white: 'white background',
    indoor: 'indoor',
    outdoor: 'outdoor',
    nature: 'nature background'
  }
  if (annotation.background) parts.push(bgMap[annotation.background])
  
  if (annotation.expression) {
    parts.push(`${annotation.expression} expression`)
  }
  
  return parts.filter(p => p).join(', ')
}
```

---

### **2.10 Caption 最佳实践指南**

**用户提示：**

```
┌──────────────────────────────────────────┐
│  💡 Caption 编写指南                      │
│                                          │
│  ✅ 应该做的：                             │
│  • 必须包含触发词                         │
│  • 描述角度（front/side/back）            │
│  • 描述姿势和背景                         │
│  • 保持简洁（10-15 词）                   │
│                                          │
│  ❌ 不应该做的：                           │
│  • 不要省略触发词                         │
│  • 不要用主观词（cute, beautiful）        │
│  • 不要过于详细                           │
│  • 不要用中文                             │
│                                          │
│  📝 标准格式：                            │
│  {trigger}, {angle} view, {pose},        │
│  {background}                             │
│                                          │
│  ✨ 示例：                                │
│  xiao_huli, front view, standing,        │
│  white background                         │
└──────────────────────────────────────────┘
```

---

## 🗂️ 三、完整训练流程概览

### **3.1 五阶段流程**

```
阶段1: 准备数据集
  ├─ 上传图片（批量）
  ├─ 批量标注（角度/表情/姿势/背景）
  ├─ 生成 Caption（模板/AI）
  └─ 人工审核修改

阶段2: 配置训练参数
  ├─ 选择训练模式（新手/标准/专家）
  ├─ 设置触发词
  └─ 调整参数（可选）

阶段3: 执行训练
  ├─ 数据集格式转换
  ├─ 启动 Kohya 训练
  ├─ 实时监控进度
  └─ 保存 Checkpoint

阶段4: 质量评估
  ├─ 生成测试图片
  ├─ 一致性评分
  └─ 生成质量报告

阶段5: 使用 LoRA
  ├─ 加载模型
  ├─ 调整权重
  └─ 生成新图片
```

---

## 📊 四、MVP 功能清单

### **必须实现（MVP）**

✅ 图片批量上传（最多 50 张）  
✅ 批量标注界面（角度/表情/姿势/背景）  
✅ 模板生成 Caption  
✅ Caption 编辑界面（逐张浏览+修改）  
✅ 保存到数据库和文件系统  
✅ 基础质量检查（数量、角度覆盖）  

### **后续版本**

⏸️ AI 自动生成 Caption  
⏸️ 智能角度识别  
⏸️ 训练失败诊断和重试  
⏸️ 训练暂停/恢复  
⏸️ 多 Checkpoint 管理  
⏸️ 高级质量评估  

---

## 📝 五、已确认决策

### **决策 1：Caption 模板固定**

✅ **决策：** 使用固定模板，不允许用户自定义

**固定模板：**
```
{trigger_word}, {angle} view, {pose}, {background}
```

**理由：**
- 保证 Caption 格式一致性
- 降低用户学习成本
- 减少配置错误的可能性
- 简化开发和测试

---

### **决策 2：AI 生成延后**

⏸️ **决策：** MVP 阶段不实现 AI 生成

**理由：**
- 增加系统复杂度
- 需要额外 API 或模型
- 模板生成已经足够好用
- 用户仍需审核，AI 优势有限

**后续计划：**
- v2.0 评估是否添加
- 根据用户反馈决定
- 候选模型：GPT-4V / Qwen-VL / BLIP

---

### **决策 3：标注必填项**

✅ **决策：**
- **必填：** 角度（angle）
- **可选：** 姿势（pose）、背景（background）
- **不使用：** 表情（expression）

**理由：**
- 角度对训练质量最重要
- pose 和 background 可增强泛化能力
- 表情增加复杂度，收益不高

---

## 🚀 六、下一步行动

1. ✅ 确认本设计方案
2. 📝 更新 IMPLEMENTATION_PLAN.md
3. 🎯 确定 MVP 功能优先级
4. 💻 开始开发

---

**文档结束**

*请审阅并提出修改意见*
