# LoRA 训练完善 + IP-Adapter 集成设计方案

**文档版本：** v1.0  
**创建日期：** 2026-05-10  
**目标：** 实现完整的 IP 孵化流程，确保 IP 可用于后续内容生成

---

## 📋 一、现状分析

### **1.1 LoRA 训练模块现状**

#### **✅ 已实现功能**
- ✅ LoRA 模型创建和管理
- ✅ 训练任务状态跟踪（pending/training/completed/failed）
- ✅ 训练参数配置（JSON 格式）
- ✅ 进度跟踪（progress, current_epoch, current_loss）
- ✅ Kohya-ss 集成框架（但使用模拟模式）
- ✅ 训练结果验证（文件大小检查）

#### **❌ 缺失功能**
1. **数据集管理缺失**
   - ❌ 没有训练数据集上传功能
   - ❌ 没有数据集质量检查
   - ❌ 没有数据增强功能
   - ❌ 没有数据集版本管理

2. **训练流程不完整**
   - ❌ Kohya-ss 集成是模拟模式
   - ❌ 没有真实的训练执行
   - ❌ 没有训练日志实时查看
   - ❌ 没有训练中断和恢复

3. **训练效果评估缺失**
   - ❌ 没有自动生成测试图片
   - ❌ 没有过拟合/欠拟合检测
   - ❌ 没有训练质量评分
   - ❌ 没有推荐最佳 checkpoint

4. **前端功能不足**
   - ❌ 没有数据集管理界面
   - ❌ 训练参数配置过于简单
   - ❌ 没有训练效果预览
   - ❌ 没有实时日志查看

---

### **1.2 IP-Adapter 服务现状**

#### **✅ 已实现功能**
- ✅ IP-Adapter 服务框架完整
- ✅ 参考图片预处理（resize, crop, pad）
- ✅ 单图/多图 IP-Adapter 生成
- ✅ LoRA + IP-Adapter 联合生成
- ✅ GPU 缓存优化
- ✅ 参数配置（ip_adapter_scale）

#### **⚠️ 需要完善**
1. **模型加载问题**
   - ⚠️ 硬编码使用 `runwayml/stable-diffusion-v1-5`
   - ⚠️ 没有本地模型支持
   - ⚠️ 模型下载没有进度显示
   - ⚠️ 没有模型版本管理

2. **一致性评估缺失**
   - ❌ 没有生成质量评估
   - ❌ 没有 IP 一致性检测
   - ❌ 没有相似度计算
   - ❌ 没有自动筛选机制

3. **多参考图融合**
   - ⚠️ 多参考图直接传入，没有权重分配
   - ⚠️ 没有角度优先级（正面 > 侧面 > 背面）
   - ⚠️ 没有特征提取和融合策略

---

## 🎯 二、设计目标

### **2.1 LoRA 训练完善目标**

```
目标：实现完整的 LoRA 训练流程，产出高质量 IP 专属模型

关键指标：
- 训练成功率 > 90%
- 训练质量评分 > 80 分
- 用户满意度 > 4.5/5
```

### **2.2 IP-Adapter 集成目标**

```
目标：实现真实的 IP 一致性保障

关键指标：
- IP 一致性评分 > 85 分
- 生成失败率 < 10%
- 参考图利用率 100%
```

### **2.3 整体 IP 孵化流程目标**

```
从创建 IP 到可用于生成的时间 < 30 分钟

完整流程：
创建 IP → 上传参考图 → 训练 LoRA → 验证效果 → IP 就绪
```

---

## 🏗️ 三、架构设计

### **3.1 整体架构图**

```
┌──────────────────────────────────────────────────────┐
│                  前端交互层                           │
│                                                      │
│  IP 创建 → 数据集管理 → 训练配置 → 训练监控 → 效果验证│
└───────────────────┬──────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────┐
│              IP 孵化服务层 (新增)                      │
│                                                      │
│  IPIncubationService                                 │
│  ├─ DatasetManager     (数据集管理)                   │
│  ├─ TrainingOrchestrator (训练编排)                   │
│  ├─ QualityAssessor    (质量评估)                     │
│  └─ ConsistencyChecker (一致性检测)                   │
└───────────────────┬──────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────┐
│              AI 引擎层                                │
│                                                      │
│  LoRATrainer          (Kohya-ss 集成)                 │
│  IPAdapterService     (IP-Adapter 集成)               │
│  ImageQualityService  (质量评估)                      │
│  FeatureExtractor     (特征提取)                      │
└───────────────────┬──────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────┐
│              基础设施层                               │
│                                                      │
│  GPU 资源管理 | 存储管理 | 任务队列 | 日志系统         │
└──────────────────────────────────────────────────────┘
```

---

## 📦 四、核心模块设计

### **4.1 数据集管理模块 (DatasetManager)**

#### **功能设计**

```python
class DatasetManager:
    """训练数据集管理"""
    
    # 1. 数据集上传
    async def upload_dataset(
        ip_asset_id: int,
        images: List[UploadFile],
        metadata: Dict  # 每张图片的标注信息
    ) -> DatasetRecord:
        """
        上传训练数据集
        
        功能：
        - 图片格式验证（JPG/PNG）
        - 图片质量检查（分辨率、清晰度）
        - 自动去重（感知哈希）
        - 元数据标注（角度、表情、动作）
        """
    
    # 2. 数据集验证
    async def validate_dataset(dataset_id: int) -> ValidationResult:
        """
        验证数据集质量
        
        检查项：
        - 图片数量（建议 15-30 张）
        - 图片质量（分辨率 >= 512x512）
        - 角度覆盖（正面、侧面、背面）
        - 多样性（表情、动作、背景）
        - 一致性（同一角色、同一风格）
        """
    
    # 3. 数据增强
    async def augment_dataset(
        dataset_id: int,
        strategies: List[str] = ['flip', 'rotate', 'color_jitter']
    ) -> int:
        """
        数据增强
        
        策略：
        - 水平翻转
        - 旋转（±15度）
        - 颜色抖动
        - 亮度调整
        - 添加噪声
        
        返回：增强后的图片数量
        """
    
    # 4. 数据集版本管理
    async def create_version(dataset_id: int) -> DatasetVersion:
        """
        创建数据集版本
        
        用途：
        - 记录每次训练使用的数据集
        - 支持回滚和对比
        - 版本间差异分析
        """
```

#### **数据模型设计**

```python
class TrainingDataset(Base):
    """训练数据集"""
    __tablename__ = "training_datasets"
    
    id = Column(Integer, primary_key=True)
    ip_asset_id = Column(Integer, ForeignKey("ip_assets.id"))
    name = Column(String(100))
    description = Column(Text)
    
    # 数据集信息
    image_count = Column(Integer)  # 图片数量
    augmented_count = Column(Integer)  # 增强后数量
    total_size_mb = Column(Float)  # 总大小
    
    # 质量评估
    quality_score = Column(Float)  # 质量评分 0-100
    angle_coverage = Column(JSON)  # {"front": 10, "side": 8, "back": 5}
    diversity_score = Column(Float)  # 多样性评分
    consistency_score = Column(Float)  # 一致性评分
    
    # 状态
    status = Column(String(20))  # pending/validating/ready/archived
    validation_report = Column(JSON)  # 验证报告
    
    # 版本管理
    version = Column(Integer, default=1)
    parent_version_id = Column(Integer, ForeignKey("training_datasets.id"))
    
    # 元数据
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class DatasetImage(Base):
    """数据集中的图片"""
    __tablename__ = "dataset_images"
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("training_datasets.id"))
    file_path = Column(String(500))
    
    # 图片信息
    width = Column(Integer)
    height = Column(Integer)
    file_size_kb = Column(Integer)
    
    # 标注信息
    angle = Column(String(20))  # front/side/back/full/half
    expression = Column(String(50))  # happy/sad/angry/surprised
    pose = Column(String(50))  # standing/sitting/running
    background = Column(String(50))  # simple/complex/outdoor/indoor
    
    # 质量评估
    quality_score = Column(Float)  # 图片质量评分
    is_augmented = Column(Boolean, default=False)  # 是否增强生成
    parent_image_id = Column(Integer, ForeignKey("dataset_images.id"))
    
    # 使用状态
    is_selected = Column(Boolean, default=True)  # 是否用于训练
    rejection_reason = Column(String(200))  # 拒绝原因
    
    created_at = Column(DateTime)
```

---

### **4.2 训练编排模块 (TrainingOrchestrator)**

#### **功能设计**

```python
class TrainingOrchestrator:
    """训练流程编排"""
    
    # 1. 训练配置生成
    async def generate_training_config(
        ip_asset_id: int,
        dataset_id: int,
        mode: str = "auto"  # auto/beginner/expert
    ) -> TrainingConfig:
        """
        生成训练配置
        
        模式：
        - auto: 基于数据集自动配置
        - beginner: 预设安全参数
        - expert: 手动配置
        
        配置项：
        - 训练步数（基于数据集大小）
        - 学习率（基于目标风格）
        - Batch size（基于 GPU 显存）
        - Network dim（基于复杂度）
        """
    
    # 2. 训练执行
    async def start_training(
        lora_id: int,
        dataset_id: int,
        config: TrainingConfig
    ) -> bool:
        """
        启动训练
        
        流程：
        1. 验证数据集
        2. 准备训练环境
        3. 生成 Kohya 配置文件
        4. 启动训练进程
        5. 监控训练进度
        6. 保存 checkpoint
        """
    
    # 3. 实时监控
    async def monitor_training(lora_id: int) -> TrainingStatus:
        """
        监控训练状态
        
        返回：
        - 当前进度
        - 当前 loss
        - GPU 使用情况
        - 预计剩余时间
        - 训练日志（最近 100 行）
        """
    
    # 4. 训练中断和恢复
    async def pause_training(lora_id: int) -> bool:
        """暂停训练，保存 checkpoint"""
    
    async def resume_training(lora_id: int) -> bool:
        """从最新 checkpoint 恢复训练"""
    
    async def cancel_training(lora_id: int) -> bool:
        """取消训练，清理资源"""
```

#### **Kohya-ss 真实集成**

```python
class KohyaIntegration:
    """Kohya-ss 真实集成"""
    
    async def run_training(self, config: KohyaConfig) -> TrainingResult:
        """
        运行 Kohya 训练
        
        步骤：
        1. 检查 Kohya-ss 安装
        2. 准备数据集（转换为 Kohya 格式）
        3. 生成配置文件
        4. 启动训练进程
        5. 实时解析日志
        6. 更新进度到数据库
        7. 处理训练结果
        """
    
    def _convert_dataset_to_kohya_format(
        self,
        dataset_path: str,
        output_path: str
    ):
        """
        转换数据集为 Kohya 格式
        
        Kohya 格式要求：
        - 目录名格式：10_character_name（重复次数_角色名）
        - 图片放在对应目录
        - 可选：caption 文件
        """
    
    def _parse_training_log(self, log_line: str) -> TrainingProgress:
        """
        解析训练日志
        
        提取：
        - Epoch 进度
        - Current loss
        - Learning rate
        - GPU 使用情况
        """
    
    async def auto_detect_kohya_path(self) -> Optional[str]:
        """
        自动检测 Kohya-ss 安装路径
        
        检测顺序：
        1. 环境变量 KOHYA_PATH
        2. 常见安装路径
        3. pip 安装的 kohya-ss
        4. Docker 容器中的 kohya-ss
        """
```

---

### **4.3 质量评估模块 (QualityAssessor)**

#### **功能设计**

```python
class QualityAssessor:
    """训练质量评估"""
    
    # 1. 自动生成测试图片
    async def generate_test_images(
        lora_id: int,
        num_images: int = 5,
        test_prompts: List[str] = None
    ) -> List[TestImage]:
        """
        生成测试图片
        
        测试场景：
        - 正面全身
        - 侧面半身
        - 不同表情
        - 不同动作
        - 不同背景
        
        默认提示词模板：
        - "character_name, full body, front view, simple background"
        - "character_name, half body, side view, smiling"
        - 等等...
        """
    
    # 2. 质量评估
    async def assess_quality(
        lora_id: int,
        test_images: List[TestImage]
    ) -> QualityReport:
        """
        评估训练质量
        
        评估维度：
        1. IP 一致性（与参考图对比）
        2. 图片质量（清晰度、色彩）
        3. 风格匹配（与目标风格对比）
        4. 过拟合检测
        5. 欠拟合检测
        
        返回：
        - 总体评分 0-100
        - 各维度评分
        - 问题诊断
        - 改进建议
        """
    
    # 3. 过拟合/欠拟合检测
    def detect_overfitting(self, training_log: TrainingLog) -> bool:
        """
        检测过拟合
        
        指标：
        - Training loss 持续下降但验证 loss 上升
        - 生成图片过于接近训练集
        - 缺乏多样性
        """
    
    def detect_underfitting(self, training_log: TrainingLog) -> bool:
        """
        检测欠拟合
        
        指标：
        - Training loss 下降缓慢
        - 生成图片与训练集差异大
        - IP 特征不明显
        """
    
    # 4. 推荐最佳 checkpoint
    async def recommend_best_checkpoint(
        lora_id: int,
        checkpoints: List[Checkpoint]
    ) -> Checkpoint:
        """
        推荐最佳 checkpoint
        
        策略：
        - 基于 loss 曲线
        - 基于测试图片质量
        - 基于泛化能力
        """
```

#### **质量评分算法**

```python
def calculate_quality_score(
    consistency_score: float,      # IP 一致性 0-100
    image_quality: float,          # 图片质量 0-100
    style_match: float,            # 风格匹配 0-100
    diversity: float,              # 多样性 0-100
    overfitting_penalty: float,    # 过拟合惩罚 0-20
    underfitting_penalty: float    # 欠拟合惩罚 0-20
) -> float:
    """
    计算总体质量评分
    
    公式：
    score = (consistency * 0.4 + 
             image_quality * 0.2 + 
             style_match * 0.2 + 
             diversity * 0.2) - 
            overfitting_penalty - 
            underfitting_penalty
    
    权重说明：
    - IP 一致性最重要（40%）
    - 图片质量、风格匹配、多样性各 20%
    - 过拟合/欠拟合惩罚
    """
```

---

### **4.4 一致性检测模块 (ConsistencyChecker)**

#### **功能设计**

```python
class ConsistencyChecker:
    """IP 一致性检测"""
    
    # 1. 特征提取
    async def extract_features(
        image_path: str,
        feature_type: str = "clip"  # clip/face/style
    ) -> FeatureVector:
        """
        提取图片特征
        
        特征类型：
        - CLIP 特征：整体语义特征
        - Face 特征：脸部特征（如果有脸）
        - Style 特征：风格特征
        """
    
    # 2. 相似度计算
    async def calculate_similarity(
        reference_features: FeatureVector,
        generated_features: FeatureVector
    ) -> float:
        """
        计算相似度
        
        方法：
        - 余弦相似度
        - 欧氏距离
        - 加权综合
        
        返回：0-100 分
        """
    
    # 3. 一致性评估
    async def check_consistency(
        ip_asset_id: int,
        generated_image_path: str
    ) -> ConsistencyReport:
        """
        检查生成图片与 IP 的一致性
        
        评估维度：
        1. 脸部一致性（如果适用）
           - 五官比例
           - 脸型
           - 发型
        
        2. 配色一致性
           - 主色调
           - 配色方案
        
        3. 风格一致性
           - 画风
           - 细节处理
        
        4. 体型一致性
           - 身高比例
           - 体型特征
        
        返回：
        - 总体一致性评分
        - 各维度评分
        - 差异分析
        """
    
    # 4. 批量一致性检查
    async def batch_check_consistency(
        ip_asset_id: int,
        image_paths: List[str]
    ) -> BatchConsistencyReport:
        """
        批量检查一致性
        
        用于：
        - 训练后批量验证
        - 生成后自动筛选
        - 内容库质量检查
        """
```

#### **特征提取实现**

```python
class FeatureExtractor:
    """特征提取器"""
    
    def __init__(self):
        # 使用预训练模型
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.face_detector = None  # 可选：面部检测
        self.style_extractor = None  # 可选：风格提取
    
    def extract_clip_features(self, image: Image.Image) -> np.ndarray:
        """
        提取 CLIP 特征
        
        返回：512 维特征向量
        """
    
    def extract_face_features(self, image: Image.Image) -> Optional[np.ndarray]:
        """
        提取面部特征
        
        使用：
        - FaceNet
        - 或 ArcFace
        
        返回：128 维面部特征向量
        """
    
    def extract_color_palette(self, image: Image.Image, n_colors: int = 5) -> List[RGB]:
        """
        提取主色调
        
        使用 K-Means 聚类
        
        返回：n 个主色
        """
```

---

### **4.5 IP-Adapter 服务增强**

#### **多参考图融合策略**

```python
class IPAdapterServiceEnhanced:
    """IP-Adapter 服务增强版"""
    
    async def generate_with_smart_reference(
        ip_asset_id: int,
        prompt: str,
        **kwargs
    ) -> GenerationResult:
        """
        智能参考图生成
        
        策略：
        1. 根据生成内容自动选择参考图
           - 生成正面图 → 使用正面参考图
           - 生成侧面图 → 使用侧面参考图
        
        2. 多参考图权重分配
           - 主要参考图：权重 0.6
           - 辅助参考图：权重 0.3
           - 风格参考图：权重 0.1
        
        3. 特征融合
           - 提取各参考图特征
           - 加权融合
           - 注入生成过程
        """
    
    def select_best_reference(
        ip_asset_id: int,
        target_angle: str = "auto",
        target_pose: str = "auto"
    ) -> List[ReferenceImage]:
        """
        选择最佳参考图
        
        优先级：
        1. 角度匹配
        2. 表情匹配
        3. 动作匹配
        4. 图片质量
        """
    
    async def adaptive_ip_adapter_scale(
        prompt: str,
        reference_images: List[str]
    ) -> float:
        """
        自适应 IP-Adapter scale
        
        策略：
        - 强调角色特征 → 高 scale (0.7-0.9)
        - 强调场景/动作 → 中 scale (0.5-0.7)
        - 自由创作 → 低 scale (0.3-0.5)
        
        基于提示词分析自动调整
        """
```

---

## 🎨 五、前端设计

### **5.1 IP 孵化工作流页面**

```
┌─────────────────────────────────────────────────┐
│  IP 孵化工作流                                    │
│                                                  │
│  Step 1: 创建 IP ──→ Step 2: 上传参考图          │
│       ✅                   ✅                    │
│                                                  │
│  Step 3: 准备数据集 ──→ Step 4: 训练 LoRA        │
│       🔄 进行中              ⏳ 待开始             │
│                                                  │
│  Step 5: 验证效果 ──→ Step 6: IP 就绪            │
│       ⏳ 待开始              ⏳ 待开始             │
└─────────────────────────────────────────────────┘
```

### **5.2 数据集管理界面**

```
┌─────────────────────────────────────────────────┐
│  数据集管理                                       │
│                                                  │
│  [上传图片] [数据增强] [验证数据集] [开始训练]     │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │ 图片网格视图                                │  │
│  │ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐            │  │
│  │ │📷 │ │📷 │ │📷 │ │📷 │ │📷 │  ...        │  │
│  │ │正面│ │侧面│ │背面│ │笑  │ │站  │            │  │
│  │ └───┘ └───┘ └───┘ └───┘ └───┘            │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  统计信息：                                       │
│  - 图片数量：23 张                                │
│  - 角度覆盖：正面 10, 侧面 8, 背面 5              │
│  - 质量评分：85/100                               │
│  - 建议：可以开始训练 ✅                          │
└─────────────────────────────────────────────────┘
```

### **5.3 训练监控界面**

```
┌─────────────────────────────────────────────────┐
│  LoRA 训练监控                                    │
│                                                  │
│  进度：████████████████░░░░ 65%                  │
│  Epoch: 6/10                                     │
│  Current Loss: 0.0423                            │
│  预计剩余：12 分钟                                 │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │ Loss 曲线图                                 │  │
│  │  ╭─                                      │  │
│  │  │  ╰──                                  │  │
│  │  │      ╰──                              │  │
│  │  └──────────────                          │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  GPU 使用：                                       │
│  - 显存：6.2GB / 8GB                             │
│  - 利用率：85%                                    │
│  - 温度：72°C                                     │
│                                                  │
│  训练日志：                                       │
│  [2026-05-10 16:30:25] Epoch 6/10, Loss: 0.0423 │
│  [2026-05-10 16:30:20] Epoch 5/10, Loss: 0.0445 │
│  [2026-05-10 16:30:15] Saving checkpoint...      │
│                                                  │
│  [暂停训练] [查看日志] [取消训练]                  │
└─────────────────────────────────────────────────┘
```

### **5.4 训练效果验证界面**

```
┌─────────────────────────────────────────────────┐
│  训练效果验证                                     │
│                                                  │
│  总体评分：88/100 ⭐⭐⭐⭐                          │
│                                                  │
│  维度评分：                                       │
│  ┌───────────────────────────────────────────┐  │
│  │ IP 一致性：    ████████████░░ 92/100       │  │
│  │ 图片质量：     ██████████░░░░ 85/100       │  │
│  │ 风格匹配：     ███████████░░░ 88/100       │  │
│  │ 多样性：       ██████████░░░░ 82/100       │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  测试图片：                                       │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐            │
│  │测试1│ │测试2│ │测试3│ │测试4│ │测试5│            │
│  │ 95 │ │ 88 │ │ 91 │ │ 82 │ │ 85 │            │
│  └────┘ └────┘ └────┘ └────┘ └────┘            │
│                                                  │
│  诊断结果：                                       │
│  ✅ 训练质量优秀，可以使用                         │
│  💡 建议：可以适当增加训练步数提升细节             │
│                                                  │
│  [重新训练] [使用此模型] [导出报告]                │
└─────────────────────────────────────────────────┘
```

---

## 📊 六、数据库设计

### **6.1 新增表**

```sql
-- 训练数据集表
CREATE TABLE training_datasets (
    id INTEGER PRIMARY KEY,
    ip_asset_id INTEGER REFERENCES ip_assets(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    image_count INTEGER,
    augmented_count INTEGER,
    total_size_mb FLOAT,
    quality_score FLOAT,
    angle_coverage JSON,
    diversity_score FLOAT,
    consistency_score FLOAT,
    status VARCHAR(20) DEFAULT 'pending',
    validation_report JSON,
    version INTEGER DEFAULT 1,
    parent_version_id INTEGER REFERENCES training_datasets(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 数据集图片表
CREATE TABLE dataset_images (
    id INTEGER PRIMARY KEY,
    dataset_id INTEGER REFERENCES training_datasets(id),
    file_path VARCHAR(500) NOT NULL,
    width INTEGER,
    height INTEGER,
    file_size_kb INTEGER,
    angle VARCHAR(20),
    expression VARCHAR(50),
    pose VARCHAR(50),
    background VARCHAR(50),
    quality_score FLOAT,
    is_augmented BOOLEAN DEFAULT FALSE,
    parent_image_id INTEGER REFERENCES dataset_images(id),
    is_selected BOOLEAN DEFAULT TRUE,
    rejection_reason VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 测试图片表
CREATE TABLE test_images (
    id INTEGER PRIMARY KEY,
    lora_model_id INTEGER REFERENCES lora_models(id),
    file_path VARCHAR(500) NOT NULL,
    prompt TEXT,
    quality_score FLOAT,
    consistency_score FLOAT,
    test_category VARCHAR(50),  -- front_view/side_view/expression/etc
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 训练检查点表
CREATE TABLE training_checkpoints (
    id INTEGER PRIMARY KEY,
    lora_model_id INTEGER REFERENCES lora_models(id),
    file_path VARCHAR(500) NOT NULL,
    epoch INTEGER,
    step INTEGER,
    loss FLOAT,
    is_recommended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **6.2 修改现有表**

```sql
-- 扩展 lora_models 表
ALTER TABLE lora_models ADD COLUMN dataset_id INTEGER REFERENCES training_datasets(id);
ALTER TABLE lora_models ADD COLUMN quality_score FLOAT;
ALTER TABLE lora_models ADD COLUMN quality_report JSON;
ALTER TABLE lora_models ADD COLUMN recommended_checkpoint_id INTEGER REFERENCES training_checkpoints(id);
```

---

## 🔄 七、完整工作流程

### **7.1 IP 孵化完整流程**

```
1. 创建 IP 资产
   ↓
2. 上传参考图（多角度）
   ↓
3. 创建训练数据集
   ├─ 上传图片
   ├─ 自动标注（角度、表情）
   ├─ 质量检查
   └─ 数据增强（可选）
   ↓
4. 验证数据集
   ├─ 数量检查（15-30 张）
   ├─ 角度覆盖检查
   ├─ 质量评分
   └─ 给出建议
   ↓
5. 配置训练参数
   ├─ 自动模式（推荐）
   ├─ 新手模式（安全参数）
   └─ 专家模式（手动配置）
   ↓
6. 启动训练
   ├─ 准备数据集
   ├─ 生成 Kohya 配置
   ├─ 启动训练进程
   └─ 实时监控
   ↓
7. 训练完成
   ├─ 保存模型
   ├─ 生成测试图片
   └─ 质量评估
   ↓
8. 验证效果
   ├─ IP 一致性检查
   ├─ 质量评分
   ├─ 问题诊断
   └─ 改进建议
   ↓
9. IP 就绪 ✅
   ├─ 关联 LoRA 模型
   ├─ 更新 IP 状态
   └─ 可用于内容生成
```

---

## 📈 八、性能优化策略

### **8.1 GPU 资源管理**

```python
class GPUResourceManager:
    """GPU 资源管理器"""
    
    # 1. 显存预估
    def estimate_vram_usage(
        batch_size: int,
        resolution: int,
        network_dim: int
    ) -> float:
        """预估训练所需显存"""
    
    # 2. 资源分配
    async def allocate_gpu(training_task_id: int) -> bool:
        """分配 GPU 资源"""
    
    # 3. 队列管理
    async def enqueue_training(task: TrainingTask):
        """训练任务排队"""
    
    # 4. 并发控制
    MAX_CONCURRENT_TRAINING = 1  # 同时只训练 1 个模型
```

### **8.2 训练加速策略**

```
1. 混合精度训练（FP16）
   - 显存占用减半
   - 速度提升 30-50%

2. 梯度累积
   - 模拟大 batch size
   - 适合小显存 GPU

3. 梯度检查点
   - 牺牲速度换显存
   - 适合 6GB 显存

4. 分布式训练（可选）
   - 多 GPU 训练
   - 速度线性提升
```

---

## 🎯 九、实施计划

### **阶段一：数据集管理（1-2 周）**

```
Week 1:
✅ 数据模型设计
✅ 数据集上传功能
✅ 图片质量检查
✅ 自动去重

Week 2:
✅ 数据增强功能
✅ 数据集验证
✅ 前端数据集管理界面
✅ 单元测试
```

### **阶段二：Kohya 集成（2-3 周）**

```
Week 3:
✅ Kohya-ss 安装检测
✅ 数据集格式转换
✅ 配置文件生成
✅ 训练进程管理

Week 4:
✅ 实时日志解析
✅ 进度更新
✅ 训练中断和恢复
✅ 错误处理

Week 5:
✅ 训练前端界面
✅ 实时监控
✅ 集成测试
```

### **阶段三：质量评估（2 周）**

```
Week 6:
✅ 测试图片生成
✅ 特征提取器
✅ 相似度计算
✅ 一致性检测

Week 7:
✅ 质量评分算法
✅ 过拟合检测
✅ 前端验证界面
✅ 优化和测试
```

### **阶段四：IP-Adapter 增强（1 周）**

```
Week 8:
✅ 多参考图融合
✅ 智能参考图选择
✅ 自适应 scale
✅ 集成测试
```

---

## 💡 十、关键决策点

### **10.1 Kohya-ss 集成方式**

**选项 A：直接调用脚本**（推荐）
- ✅ 简单直接
- ✅ 易于调试
- ❌ 需要用户安装 Kohya-ss

**选项 B：Docker 容器**
- ✅ 环境隔离
- ✅ 无需用户安装
- ❌ 体积大，启动慢

**决策：** 选项 A，提供安装指导

---

### **10.2 特征提取模型选择**

**选项 A：CLIP**（推荐）
- ✅ 通用性强
- ✅ 预训练模型可用
- ✅ 适合风格匹配

**选项 B：FaceNet**
- ✅ 面部识别准确
- ❌ 仅适用于有脸的角色

**决策：** 组合使用，CLIP 为主，FaceNet 为辅

---

### **10.3 数据集存储方式**

**选项 A：本地文件系统**（推荐）
- ✅ 简单
- ✅ 快速
- ❌ 不适合大规模

**选项 B：对象存储（S3）**
- ✅ 可扩展
- ❌ 复杂度高

**决策：** 选项 A，后续可迁移到 S3

---

## 📝 十一、风险和挑战

### **技术风险**

1. **Kohya-ss 兼容性**
   - 风险：版本更新导致 API 变化
   - 缓解：版本锁定，定期测试

2. **GPU 显存不足**
   - 风险：训练失败
   - 缓解：显存预估，自动调整参数

3. **训练质量不稳定**
   - 风险：模型效果差
   - 缓解：自动评估，重新训练建议

### **用户体验风险**

1. **学习曲线陡峭**
   - 风险：用户流失
   - 缓解：新手引导，自动模式

2. **训练时间长**
   - 风险：用户不耐烦
   - 缓解：进度展示，时间预估，后台训练

---

## ✅ 十二、成功标准

### **功能指标**

- ✅ 数据集上传成功率 > 95%
- ✅ 训练成功率 > 90%
- ✅ 质量评分准确率 > 85%
- ✅ IP 一致性评分 > 85

### **性能指标**

- ✅ 训练启动时间 < 30 秒
- ✅ 进度更新延迟 < 5 秒
- ✅ 质量评估时间 < 2 分钟

### **用户指标**

- ✅ 用户满意度 > 4.5/5
- ✅ IP 孵化完成率 > 80%
- ✅ 训练模型使用率 > 70%

---

## 🚀 十三、下一步行动

1. **确认设计方案** - 审查并确认此设计文档
2. **创建开发任务** - 拆分任务到具体工单
3. **开始实施** - 从数据集管理模块开始
4. **持续迭代** - 根据反馈调整

---

**文档状态：** 待审核  
**审核人：** [待填写]  
**审核日期：** [待填写]
