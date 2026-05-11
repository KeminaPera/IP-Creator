# IP 资产特征库设计文档

**文档版本：** v1.0  
**创建日期：** 2026-05-10  
**状态：** 📝 设计阶段

---

## 🎯 一、问题分析

### **1.1 当前设计的不足**

**现有 IPAsset 模型：**
```python
reference_images = Column(JSON)  # 只存储了基础参考图
positive_tags = Column(JSON)     # 简单的标签列表
negative_tags = Column(JSON)     # 简单的标签列表
```

**问题：**
- ❌ 参考图和多视图混在一起，没有明确区分
- ❌ 没有管理服装、表情、动作等多维度特征
- ❌ 训练 LoRA 时无法精确控制要包含哪些特征
- ❌ 生成图片时无法指定"穿什么衣服"、"什么表情"

---

### **1.2 用户需求场景**

**场景 1：训练 LoRA 时需要多样化数据**
```
用户希望训练"小狐狸"的 LoRA，包含：
- 基础外观（必须）
- 3 种服装（常服、和服、机甲）
- 5 种表情（开心、生气、惊讶、伤心、中性）
- 4 种动作（站立、坐着、跑步、跳跃）

这样生成的 LoRA 才能在不同场景下使用
```

**场景 2：生成图片时精确控制**
```
用户生成图片时希望指定：
"小狐狸穿着和服，开心的表情，在森林里"

如果 LoRA 训练时没有包含"和服"和"开心"的数据
就无法生成符合要求的图片
```

---

## 📊 二、完整业务流程重新设计

### **2.1 五步流程**

```
┌─────────────────────────────────────────────────────┐
│  步骤 1: 创建 IP 资产（基础信息）                      │
│  - IP 名称、描述、分类                                │
│  - 触发词（Trigger Word）                            │
│  - 上传基础参考图（1-4 张）                           │
│  - 选择风格模板（3D 卡通/盲盒/治愈等）                │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  步骤 2: 生成/上传多视图                              │
│  方式 A：基于参考图 AI 生成三视图                      │
│  方式 B：手动上传三视图/多视图                        │
│  - 正面（front）                                     │
│  - 侧面（side）                                      │
│  - 背面（back）                                      │
│  - 可选：3/4 侧面等                                  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  步骤 3: 扩展特征库（服装/表情/动作）                  │
│  - 添加服装变体（常服、和服、机甲...）                 │
│  - 添加表情变体（开心、生气、惊讶...）                 │
│  - 添加动作变体（站立、坐着、跑步...）                 │
│  - 每种变体都需要上传图片或生成                       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  步骤 4: 准备训练数据集                               │
│  - 从 IP 特征库中选择要包含的特征                      │
│  - 自动组合生成多样化训练图片                          │
│  - 例如：3 视图 × 3 服装 × 5 表情 × 4 动作 = 180 张  │
│  - 标注角度、服装、表情、动作                          │
│  - 生成 Caption                                      │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  步骤 5: 训练 LoRA                                   │
│  - 使用包含多维度特征的数据集                          │
│  - 训练出能理解服装/表情/动作的模型                    │
│  - 生成时可通过提示词控制                             │
└─────────────────────────────────────────────────────┘
```

---

## 🗂️ 三、数据模型设计

### **3.1 核心概念**

```
IP 资产（IPAsset）
  │
  ├─ 基础信息（名称、描述、触发词）
  │
  ├─ 参考图片（ReferenceImages）- 用于 IP-Adapter
  │   └─ 1-4 张代表性图片
  │
  ├─ 多视图（MultiViews）- 用于展示和生成
  │   ├─ 正面图
  │   ├─ 侧面图
  │   └─ 背面图
  │
  └─ 特征库（FeatureLibrary）- 用于训练 LoRA
      ├─ 服装库（Outfits）
      ├─ 表情库（Expressions）
      └─ 动作库（Poses）
```

---

### **3.2 数据库表设计**

#### **表 1：ip_assets（修改现有表）**

```sql
CREATE TABLE ip_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 基础信息
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),  -- pet/human/fantasy
    description TEXT,
    trigger_word VARCHAR(100) NOT NULL UNIQUE,
    style_template VARCHAR(50),  -- 3d_cartoon/blind_box/healing
    
    -- 参考图（用于 IP-Adapter）
    reference_images JSON NOT NULL,
    -- 格式：[{"angle": "front", "path": "/path.jpg", "is_primary": true}]
    
    -- 正负标签
    positive_tags JSON,  -- ["cute", "fluffy", "cartoon"]
    negative_tags JSON,  -- ["realistic", "scary", "dark"]
    
    -- LoRA 关联
    lora_model_id INTEGER,
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (lora_model_id) REFERENCES lora_models(id)
);
```

---

#### **表 2：ip_multi_views（新表 - 多视图）**

```sql
CREATE TABLE ip_multi_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_asset_id INTEGER NOT NULL,
    
    -- 视图类型
    view_type VARCHAR(20) NOT NULL,  
    -- front / side / back / three_quarter_front / three_quarter_back
    
    -- 图片信息
    image_path VARCHAR(500) NOT NULL,
    width INTEGER,
    height INTEGER,
    
    -- 来源
    source VARCHAR(20) NOT NULL,  
    -- generated（AI 生成）/ uploaded（用户上传）
    
    -- 生成参数（如果是 AI 生成的）
    generation_params JSON,
    -- {"prompt": "...", "seed": 123, "model": "sd1.5"}
    
    -- 状态
    is_primary BOOLEAN DEFAULT FALSE,  -- 是否作为主要展示图
    quality_score FLOAT,  -- 质量评分 0-100
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (ip_asset_id) REFERENCES ip_assets(id) ON DELETE CASCADE
);

CREATE INDEX idx_multi_views_ip ON ip_multi_views(ip_asset_id);
CREATE INDEX idx_multi_views_type ON ip_multi_views(view_type);
```

---

#### **表 3：ip_feature_library（新表 - 特征库）**

```sql
CREATE TABLE ip_feature_library (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_asset_id INTEGER NOT NULL,
    
    -- 特征类型
    feature_type VARCHAR(20) NOT NULL,
    -- outfit（服装）/ expression（表情）/ pose（动作）/ background（背景）
    
    -- 特征名称
    feature_name VARCHAR(100) NOT NULL,
    -- "casual_wear" / "kimono" / "mecha_suit"
    -- "happy" / "angry" / "surprised"
    -- "standing" / "sitting" / "running"
    
    -- 显示名称
    display_name VARCHAR(100),
    -- "常服" / "和服" / "机甲"
    -- "开心" / "生气" / "惊讶"
    -- "站立" / "坐着" / "跑步"
    
    -- 描述
    description TEXT,
    
    -- 触发词（用于生成时调用）
    trigger_phrase VARCHAR(200),
    -- "wearing casual clothes" / "wearing kimono"
    -- "happy expression" / "angry face"
    -- "standing pose" / "sitting pose"
    
    -- 参考图片（该特征的示例图）
    reference_images JSON,
    -- [{"angle": "front", "path": "/path.jpg"}]
    -- 至少需要正面图，可选侧面/背面
    
    -- 是否启用
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (ip_asset_id) REFERENCES ip_assets(id) ON DELETE CASCADE,
    UNIQUE(ip_asset_id, feature_type, feature_name)
);

CREATE INDEX idx_feature_library_ip ON ip_feature_library(ip_asset_id);
CREATE INDEX idx_feature_library_type ON ip_feature_library(feature_type);
```

---

#### **表 4：ip_feature_images（新表 - 特征图片）**

```sql
CREATE TABLE ip_feature_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id INTEGER NOT NULL,
    
    -- 角度
    angle VARCHAR(20) NOT NULL,
    -- front / side / back
    
    -- 图片路径
    image_path VARCHAR(500) NOT NULL,
    width INTEGER,
    height INTEGER,
    
    -- 来源
    source VARCHAR(20) NOT NULL,
    -- generated / uploaded
    
    -- 生成参数
    generation_params JSON,
    
    -- 质量
    quality_score FLOAT,
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (feature_id) REFERENCES ip_feature_library(id) ON DELETE CASCADE
);

CREATE INDEX idx_feature_images_feature ON ip_feature_images(feature_id);
CREATE INDEX idx_feature_images_angle ON ip_feature_images(angle);
```

---

### **3.3 数据关系图**

```
ip_assets
    │
    ├── 1:N ──→ ip_multi_views（多视图）
    │              └─ 每个 IP 有 3-5 张标准视图
    │
    └── 1:N ──→ ip_feature_library（特征库）
                   │
                   ├── outfit_1（常服）
                   │     └── 1:N ──→ ip_feature_images
                   │                    ├─ front.jpg
                   │                    ├─ side.jpg
                   │                    └─ back.jpg
                   │
                   ├── outfit_2（和服）
                   │     └── 1:N ──→ ip_feature_images
                   │
                   ├── expression_1（开心）
                   │     └── 1:N ──→ ip_feature_images
                   │
                   └── pose_1（站立）
                         └── 1:N ──→ ip_feature_images
```

---

## 🎨 四、前端页面设计

### **4.1 IP 资产管理页面（重构）**

```
┌──────────────────────────────────────────────────────────┐
│  🎨 IP 资产管理                                           │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  📋 基础信息                                        │  │
│  │                                                    │  │
│  │  IP 名称：[小狐狸____________]                      │  │
│  │  分类：[宠物 ▼]  风格：[3D 卡通 ▼]                 │  │
│  │  触发词：[xiao_huli_character_________]            │  │
│  │  描述：[_________________________________]         │  │
│  │                                                    │  │
│  │  参考图（用于 IP-Adapter）：                         │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐                          │  │
│  │  │[+添加]│ │图片1 │ │图片2 │                       │  │
│  │  │      │ │正面  │ │侧面  │                       │  │
│  │  └─────┘ └─────┘ └─────┘                          │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [保存基础信息] [下一步：多视图 ▶]                        │
└──────────────────────────────────────────────────────────┘
```

---

### **4.2 多视图管理页面**

```
┌──────────────────────────────────────────────────────────┐
│  📐 多视图管理 - 小狐狸                                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  生成方式：                                         │  │
│  │  ◉ 基于参考图 AI 生成                               │  │
│  │  ○ 手动上传图片                                     │  │
│  │                                                    │  │
│  │  [生成三视图]                                       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  当前多视图：                                       │  │
│  │                                                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │  │
│  │  │  正面    │ │  侧面    │ │  背面    │           │  │
│  │  │ [图片]   │ │ [图片]   │ │ [图片]   │           │  │
│  │  │          │ │          │ │          │           │  │
│  │  │ [重新生成]│ │ [重新生成]│ │ [重新生成]│           │  │
│  │  │ [上传替换]│ │ [上传替换]│ │ [上传替换]│           │  │
│  │  └──────────┘ └──────────┘ └──────────┘           │  │
│  │                                                    │  │
│  │  质量评分：⭐⭐⭐⭐⭐ 92/100                     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [◀ 上一步] [保存] [下一步：特征库 ▶]                     │
└──────────────────────────────────────────────────────────┘
```

---

### **4.3 特征库管理页面（核心）**

```
┌──────────────────────────────────────────────────────────┐
│  🎭 特征库管理 - 小狐狸                                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  👗 服装库（Outfits）                                │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │ 常服 (casual_wear)               [编辑][删除] │  │  │
│  │  │ 触发词：wearing casual clothes                │  │  │
│  │  │ 图片：[正面✓] [侧面✓] [背面✓]                  │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │ 和服 (kimono)                    [编辑][删除] │  │  │
│  │  │ 触发词：wearing traditional kimono            │  │  │
│  │  │ 图片：[正面✓] [侧面✓] [背面✗]  [添加背面图]   │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  │                                                    │  │
│  │  [+ 添加服装]                                       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  😊 表情库（Expressions）                            │  │
│  │                                                    │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │  │
│  │  │ 中性    │ │ 开心    │ │ 生气    │ │ 惊讶    │  │  │
│  │  │ neutral │ │ happy   │ │ angry   │ │surprised│  │  │
│  │  │ [图片]  │ │ [图片]  │ │ [图片]  │ │ [图片]  │  │  │
│  │  │ [编辑]  │ │ [编辑]  │ │ [编辑]  │ │ [编辑]  │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │  │
│  │                                                    │  │
│  │  [+ 添加表情]                                       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  🏃 动作库（Poses）                                  │  │
│  │                                                    │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │  │
│  │  │ 站立    │ │ 坐着    │ │ 跑步    │ │ 跳跃    │  │  │
│  │  │standing │ │ sitting │ │ running │ │ jumping │  │  │
│  │  │ [图片]  │ │ [图片]  │ │ [图片]  │ │ [图片]  │  │  │
│  │  │ [编辑]  │ │ [编辑]  │ │ [编辑]  │ │ [编辑]  │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘  │  │
│  │                                                    │  │
│  │  [+ 添加动作]                                       │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [◀ 上一步] [保存] [下一步：训练数据集 ▶]                 │
└──────────────────────────────────────────────────────────┘
```

---

### **4.4 添加特征对话框**

```
┌──────────────────────────────────────────┐
│  添加服装                                │
│                                          │
│  服装名称：[常服____________]             │
│  英文名称：[casual_wear______]            │
│  （用于触发词，英文，无空格）              │
│                                          │
│  触发词短语：                             │
│  [wearing casual clothes_________]       │
│  （生成图片时使用的描述）                  │
│                                          │
│  描述：                                   │
│  [日常休闲服装_________________]          │
│                                          │
│  上传参考图（至少正面）：                  │
│  ┌─────┐ ┌─────┐ ┌─────┐                │
│  │[+正面]│ │[+侧面]│ │[+背面]│            │
│  │      │ │      │ │      │              │
│  └─────┘ └─────┘ └─────┘                │
│                                          │
│  或者 [AI 生成三视图]                     │
│                                          │
│  [取消] [保存]                            │
└──────────────────────────────────────────┘
```

---

## 🔄 五、特征库在 LoRA 训练中的应用

### **5.1 训练数据集生成流程**

```
用户选择要包含的特征：
┌─────────────────────────────────────┐
│  选择训练特征                         │
│                                     │
│  ☑ 服装：                            │
│    ☑ 常服                            │
│    ☑ 和服                            │
│    ☐ 机甲（未准备好，跳过）           │
│                                     │
│  ☑ 表情：                            │
│    ☑ 中性                            │
│    ☑ 开心                            │
│    ☑ 生气                            │
│    ☐ 惊讶（未准备好，跳过）           │
│                                     │
│  ☑ 动作：                            │
│    ☑ 站立                            │
│    ☑ 坐着                            │
│    ☐ 跑步（未准备好，跳过）           │
│    ☐ 跳跃（未准备好，跳过）           │
│                                     │
│  将生成：2 服装 × 3 表情 × 2 动作    │
│        × 3 角度 = 36 张训练图片       │
│                                     │
│  [生成训练数据集]                     │
└─────────────────────────────────────┘
           ↓
自动生成组合：
┌─────────────────────────────────────┐
│  训练数据预览                         │
│                                     │
│  常服 + 中性 + 站立 + 正面           │
│  → Caption: trigger, front view,    │
│    standing, wearing casual clothes, │
│    neutral expression                │
│                                     │
│  常服 + 中性 + 站立 + 侧面           │
│  → Caption: trigger, side view,     │
│    standing, wearing casual clothes, │
│    neutral expression                │
│                                     │
│  常服 + 开心 + 坐着 + 正面           │
│  → Caption: trigger, front view,    │
│    sitting, wearing casual clothes,  │
│    happy expression                  │
│                                     │
│  ... (共 36 张)                      │
│                                     │
│  [确认并继续]                         │
└─────────────────────────────────────┘
```

---

### **5.2 Caption 生成增强**

**增强版模板：**
```
{trigger_word}, {angle} view, {pose}, {outfit_trigger}, {expression_trigger}
```

**生成示例：**
```
输入：
  trigger_word: xiao_huli_character
  angle: front
  pose: standing
  outfit: wearing casual clothes
  expression: happy expression

输出：
  xiao_huli_character, front view, standing, 
  wearing casual clothes, happy expression
```

**效果：**
- 训练时，模型学习到"服装"和"表情"也是可变特征
- 生成时，可以通过提示词控制服装和表情

---

### **5.3 生成时的应用**

```
用户生成图片：

提示词：
"xiao_huli_character, wearing kimono, happy expression, 
 sitting in garden"

模型理解：
- xiao_huli_character → 角色外观
- wearing kimono → 使用和服特征
- happy expression → 使用开心表情
- sitting → 坐姿
- in garden → 场景（新组合）

生成结果：
✅ 小狐狸穿着和服
✅ 开心的表情
✅ 坐在花园里
✅ 角色一致性保持
```

---

## 📊 六、API 接口设计

### **6.1 多视图管理**

```python
# 生成三视图
POST /api/v1/ip/{ip_id}/generate-multi-views
Response: {
  "success": true,
  "data": {
    "task_ids": {"front": "xxx", "side": "xxx", "back": "xxx"}
  }
}

# 上传视图
POST /api/v1/ip/{ip_id}/multi-views
Request: multipart/form-data
  - view_type: front/side/back
  - image: File

# 获取多视图
GET /api/v1/ip/{ip_id}/multi-views
Response: {
  "success": true,
  "data": {
    "views": [
      {"view_type": "front", "image_path": "...", "quality_score": 92}
    ]
  }
}
```

---

### **6.2 特征库管理**

```python
# 创建特征
POST /api/v1/ip/{ip_id}/features
Request: {
  "feature_type": "outfit",
  "feature_name": "kimono",
  "display_name": "和服",
  "trigger_phrase": "wearing traditional kimono",
  "description": "日本传统服装"
}

# 添加特征图片
POST /api/v1/features/{feature_id}/images
Request: multipart/form-data
  - angle: front/side/back
  - image: File
  - source: uploaded/generated

# 获取特征库
GET /api/v1/ip/{ip_id}/features?feature_type=outfit
Response: {
  "success": true,
  "data": {
    "features": [
      {
        "id": 1,
        "feature_type": "outfit",
        "feature_name": "casual_wear",
        "display_name": "常服",
        "trigger_phrase": "wearing casual clothes",
        "images": [
          {"angle": "front", "image_path": "..."},
          {"angle": "side", "image_path": "..."}
        ]
      }
    ]
  }
}

# 删除特征
DELETE /api/v1/features/{feature_id}
```

---

## 🎯 七、实现优先级

### **Phase 1：基础功能（MVP）**

✅ IP 资产基础信息管理（已有，需优化）  
✅ 多视图上传（手动）  
✅ 特征库 CRUD  
  - 服装库管理  
  - 表情库管理  
  - 动作库管理  
✅ 特征图片上传  
✅ 训练数据集生成（基于特征组合）  

---

### **Phase 2：AI 增强**

⏸️ AI 生成三视图  
⏸️ AI 生成特征图片  
⏸️ 智能标注（角度识别）  
⏸️ 质量自动评分  

---

### **Phase 3：训练集成**

⏸️ 增强版 Caption 生成（包含特征触发词）  
⏸️ 特征选择界面（训练时）  
⏸️ 训练数据集自动组合生成  
⏸️ 质量检查和优化建议  

---

## 📝 八、关键设计决策

### **决策 1：参考图 vs 多视图 vs 特征图**

**区分：**
- **参考图**（reference_images）：用于 IP-Adapter，1-4 张精华图
- **多视图**（multi_views）：标准三视图，用于展示和基础生成
- **特征图**（feature_images）：训练 LoRA 用，包含服装/表情/动作变化

**原因：**
- 用途不同，质量要求不同
- IP-Adapter 需要最代表性的图
- LoRA 训练需要多样化的图

---

### **决策 2：特征触发词设计**

**每个特征都有独立的 trigger_phrase：**
```
服装："wearing casual clothes" / "wearing kimono"
表情："happy expression" / "angry face"
动作："standing pose" / "sitting pose"
```

**好处：**
- 生成时精确控制
- Caption 自动生成
- 模型学习更清晰

---

### **决策 3：特征完整性检查**

**训练前检查：**
```
✅ 完整特征（3 角度都有）：参与训练
⚠️ 不完整特征（缺少角度）：警告，但仍可使用
❌ 未准备特征：不参与训练
```

---

### **决策 4：特征类型可扩展设计 ⭐**

**设计原则：**
- 特征类型不硬编码，支持动态扩展
- 新增特征类型无需修改数据库结构
- 前端自动适配新特征类型

**实现方案：**

#### **4.1 数据库层面**

```sql
-- feature_type 使用 VARCHAR 而非 ENUM
feature_type VARCHAR(50) NOT NULL,
-- 允许任意字符串值，不限制预设选项
```

**当前支持的类型：**
- `outfit` - 服装
- `expression` - 表情
- `pose` - 动作

**未来可扩展的类型：**
- `accessory` - 配饰（眼镜、帽子、首饰）
- `hairstyle` - 发型
- `background` - 背景场景
- `prop` - 道具（武器、工具）
- `weather` - 天气效果
- `lighting` - 光照效果
- `season` - 季节（春夏秋冬）
- `age` - 年龄变化（幼年/成年/老年）
- 等等...

**无需修改数据库，直接添加新类型即可！**

---

#### **4.2 后端配置层面**

**特征类型配置文件：**

```python
# app/config/feature_types.py

FEATURE_TYPE_CONFIG = {
    "outfit": {
        "display_name": "服装",
        "display_name_en": "Outfit",
        "icon": "👗",
        "trigger_template": "wearing {feature_name}",
        "required": True,  # 训练时是否必须
        "min_images": 3,   # 最少图片数（正面/侧面/背面）
        "caption_position": 3,  # 在 Caption 中的位置
        "description": "角色的服装变体"
    },
    "expression": {
        "display_name": "表情",
        "display_name_en": "Expression",
        "icon": "😊",
        "trigger_template": "{feature_name} expression",
        "required": True,
        "min_images": 1,  # 表情只需要正面
        "caption_position": 4,
        "description": "角色的表情变化"
    },
    "pose": {
        "display_name": "动作",
        "display_name_en": "Pose",
        "icon": "🏃",
        "trigger_template": "{feature_name} pose",
        "required": True,
        "min_images": 3,
        "caption_position": 2,
        "description": "角色的动作姿态"
    },
    # 未来新增特征类型，只需在这里添加配置：
    "accessory": {
        "display_name": "配饰",
        "display_name_en": "Accessory",
        "icon": "👓",
        "trigger_template": "wearing {feature_name}",
        "required": False,
        "min_images": 1,
        "caption_position": 5,
        "description": "角色的配饰（眼镜、帽子等）"
    },
    "background": {
        "display_name": "背景",
        "display_name_en": "Background",
        "icon": "🏞️",
        "trigger_template": "in {feature_name}",
        "required": False,
        "min_images": 1,
        "caption_position": 6,
        "description": "背景场景"
    }
}
```

**动态获取特征类型：**

```python
@router.get("/feature-types")
async def get_feature_types():
    """获取所有支持的特征类型"""
    return success_response(
        data={
            "types": [
                {
                    "type": key,
                    **value
                }
                for key, value in FEATURE_TYPE_CONFIG.items()
            ]
        }
    )
```

---

#### **4.3 前端自动适配**

**动态渲染特征库页面：**

```javascript
// 从后端获取特征类型配置
const featureTypes = ref([])

onMounted(async () => {
  const res = await getFeatureTypes()
  featureTypes.value = res.data.types
})

// 动态渲染每个特征类型
<template>
  <div v-for="type in featureTypes" :key="type.type" class="feature-section">
    <h3>{{ type.icon }} {{ type.display_name }}（{{ type.display_name_en }}）</h3>
    <p>{{ type.description }}</p>
    
    <!-- 特征列表 -->
    <div class="feature-list">
      <!-- ... -->
    </div>
    
    <!-- 添加按钮 -->
    <button @click="addFeature(type.type)">
      {{ type.icon }} 添加{{ type.display_name }}
    </button>
  </div>
</template>
```

**好处：**
- 后端添加新特征类型配置后，前端自动显示
- 无需修改前端代码
- 图标、名称、描述都从配置读取

---

#### **4.4 Caption 生成自动适配**

**动态 Caption 模板：**

```python
def generate_caption_dynamic(
    trigger_word: str,
    features: dict  # {"pose": "standing", "outfit": "kimono", ...}
) -> str:
    """
    动态生成 Caption，支持任意特征组合
    """
    parts = [trigger_word]
    
    # 按照 caption_position 排序
    sorted_features = sorted(
        features.items(),
        key=lambda x: FEATURE_TYPE_CONFIG[x[0]].get('caption_position', 99)
    )
    
    for feature_type, feature_value in sorted_features:
        config = FEATURE_TYPE_CONFIG[feature_type]
        template = config['trigger_template']
        caption_part = template.format(feature_name=feature_value)
        parts.append(caption_part)
    
    return ', '.join(parts)

# 使用示例：
caption = generate_caption_dynamic(
    "xiao_huli_character",
    {
        "angle": "front view",
        "pose": "standing",
        "outfit": "kimono",
        "expression": "happy",
        "accessory": "glasses"  # 新增特征，自动支持！
    }
)

# 输出：
# xiao_huli_character, standing pose, front view, 
# wearing kimono, happy expression, wearing glasses
```

---

#### **4.5 扩展示例：添加"配饰"特征**

**只需 3 步：**

**步骤 1：添加配置（1 分钟）**

```python
# app/config/feature_types.py
FEATURE_TYPE_CONFIG["accessory"] = {
    "display_name": "配饰",
    "display_name_en": "Accessory",
    "icon": "👓",
    "trigger_template": "wearing {feature_name}",
    "required": False,
    "min_images": 1,
    "caption_position": 5,
    "description": "角色的配饰（眼镜、帽子、首饰等）"
}
```

**步骤 2：前端自动显示**

无需修改代码，重启后前端自动显示"配饰"区块

**步骤 3：用户开始使用**

```
用户操作：
1. 进入特征库管理页面
2. 看到新增的"👓 配饰（Accessory）"区块
3. 点击"添加配饰"
4. 输入：
   - 名称：glasses
   - 显示名：眼镜
   - 触发词：wearing glasses
   - 上传图片
5. 保存

训练时：
- 选择包含"眼镜"特征
- 自动生成 Caption：
  "xiao_huli_character, front view, standing, 
   wearing casual clothes, wearing glasses"

生成时：
- 提示词："xiao_huli_character, wearing glasses"
- 生成戴眼镜的小狐狸 ✅
```

**完全不需要修改数据库和代码逻辑！**

---

#### **4.6 未来特征类型建议**

**高优先级：**
- `accessory` - 配饰（眼镜、帽子、首饰）
- `background` - 背景场景（森林、城市、室内）
- `hairstyle` - 发型（长发、短发、辫子）

**中优先级：**
- `prop` - 道具（武器、工具、宠物）
- `weather` - 天气（晴天、雨天、雪天）
- `lighting` - 光照（日光、月光、霓虹灯）

**低优先级：**
- `season` - 季节（春、夏、秋、冬）
- `age` - 年龄（幼年、成年、老年）
- `emotion_state` - 情绪状态（兴奋、疲惫、紧张）
- `camera_angle` - 拍摄角度（俯视、仰视、特写）

**每种新特征类型的添加成本：**
- 数据库：0 改动（已支持）
- 后端：1 个配置项（5 行代码）
- 前端：0 改动（自动适配）
- 总计：< 10 分钟

---

## 🚀 十、下一步行动

1. ✅ 确认本设计方案
2. 📝 创建数据库迁移脚本
   - ip_multi_views 表
   - ip_feature_library 表  
   - ip_feature_images 表
3. 💻 后端开发
   - 特征类型配置系统
   - 特征库 CRUD API
   - Caption 动态生成
4. 🎨 前端开发
   - 特征库管理页面
   - 动态渲染组件
   - 训练数据集选择界面
5. 🧪 测试
   - 新增特征类型测试（验证扩展性）
   - Caption 生成测试
   - 训练集成测试

---

## 💎 十一、设计亮点总结

### **1. 强大的可扩展性 ⭐⭐⭐⭐⭐**

**新增特征类型只需 3 步：**
1. 添加配置（5 行代码）
2. 前端自动显示（0 改动）
3. 立即可以使用

**扩展示例：**
```
添加“配饰”特征：
- 数据库：0 改动 ✅
- 后端：1 个配置项 ✅
- 前端：0 改动 ✅
- 总计：< 10 分钟 ⚡
```

---

### **2. 清晰的数据分层**

```
IP 资产
  ├─ 参考图（IP-Adapter）
  ├─ 多视图（展示/生成）
  └─ 特征库（LoRA 训练）
      ├─ 服装
      ├─ 表情
      ├─ 动作
      └─ ...（无限扩展）
```

---

### **3. 智能 Caption 生成**

**动态模板：**
- 根据选择的特征自动组合
- 位置自动排序
- 格式统一规范

**示例：**
```
基础：xiao_huli_character, front view
+ 动作：+ standing pose
+ 服装：+ wearing kimono
+ 表情：+ happy expression
+ 配饰：+ wearing glasses

结果：xiao_huli_character, standing pose, front view, 
      wearing kimono, happy expression, wearing glasses
```

---

### **4. 灵活的训练组合**

**用户自由选择：**
```
训练版本 1（基础版）：
- 服装：常服
- 表情：中性
- 动作：站立
→ 12 张图片

训练版本 2（完整版）：
- 服装：常服 + 和服 + 机甲
- 表情：5 种
- 动作：4 种
→ 180 张图片
```

---

### **5. 精确的生成控制**

**提示词控制：**
```
"xiao_huli_character, wearing kimono, happy expression, 
 sitting in garden"

✅ 角色一致性
✅ 服装指定
✅ 表情指定
✅ 姿势指定
✅ 场景自由发挥
```

---

**文档结束**

*请审阅并提出修改意见*
