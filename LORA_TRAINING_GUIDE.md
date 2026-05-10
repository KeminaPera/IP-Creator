# LoRA训练完整指南

## 📚 一、什么是LoRA？

### 1.1 核心概念

**LoRA (Low-Rank Adaptation)** 是一种高效的模型微调技术：

```
传统微调：修改模型所有参数（数十亿个）
    ↓
需要：大量GPU显存、长时间训练、大存储空间

LoRA微调：只训练一小部分新增参数（注入层）
    ↓
只需：8GB显存、2-4小时、小文件（50-200MB）
```

### 1.2 为什么用LoRA？

| 对比项 | 传统微调 | LoRA微调 |
|--------|---------|----------|
| **显存需求** | 24GB+ | 8GB+ |
| **训练时间** | 1-2天 | 2-4小时 |
| **模型大小** | 2-7GB | 50-200MB |
| **可训练数量** | 1-2个 | 数十个 |
| **切换成本** | 加载完整模型 | 只加载小权重 |

**应用场景**：
- ✅ 训练专属IP角色（保持一致性）
- ✅ 训练特定画风（动漫、写实、水彩）
- ✅ 训练特定物体（产品、建筑）
- ✅ 训练特定风格（盲盒、像素、油画）

---

## 🎯 二、训练前准备

### 2.1 硬件要求

**最低配置**：
```
GPU: NVIDIA GTX 1080Ti (11GB显存)
RAM: 16GB
存储: 50GB可用空间
```

**推荐配置**：
```
GPU: NVIDIA RTX 3090/4090 (24GB显存)
RAM: 32GB
存储: 100GB SSD
```

**检查你的GPU**：
```bash
# Windows
nvidia-smi
```

**如果没有GPU？**
- 使用云GPU服务：
  - AutoDL（国内）：https://www.autodl.com/ （约¥2/小时）
  - Google Colab（国外）：https://colab.research.google.com/
  - RunPod：https://runpod.io/

---

### 2.2 软件安装

#### **方案A：Kohya_ss（推荐，图形界面）**

**Windows安装**：
```powershell
# 1. 克隆仓库
git clone https://github.com/bmaltais/kohya_ss.git
cd kohya_ss

# 2. 运行安装脚本
.\setup.bat

# 3. 启动
.\gui.bat
```

**访问界面**：http://localhost:7860

---

#### **方案B：命令行安装**

```powershell
# 1. 创建Python环境
python -m venv lora_env
lora_env\Scripts\activate

# 2. 安装依赖
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install diffusers transformers accelerate bitsandbytes
pip install safetensors lion-pytorch dadaptation

# 3. 克隆训练脚本
git clone https://github.com/kohya-ss/sd-scripts.git
cd sd-scripts
pip install -r requirements.txt
```

---

### 2.3 下载基础模型

**推荐基础模型**：

| 模型名称 | 大小 | 用途 | 下载链接 |
|---------|------|------|---------|
| **Stable Diffusion 1.5** | 2GB | 通用，速度快 | [Civitai](https://civitai.com/models/4201) |
| **Anything V5** | 2GB | 动漫风格 | [Civitai](https://civitai.com/models/6602) |
| **DreamShaper** | 2GB | 艺术风格 | [Civitai](https://civitai.com/models/4384) |
| **Animagine XL** | 7GB | 高质量动漫 | [Civitai](https://civitai.com/models/241649) |

**下载位置**：
```
项目目录/models/stable-diffusion/
├─ v1-5-pruned.ckpt
├─ anything-v5-fp16.safetensors
└─ dreamshaper_8.safetensors
```

---

## 📸 三、准备训练数据集

### 3.1 数据集要求

**图片数量**：
```
最低要求：15张（简单角色）
推荐数量：30-50张（高质量）
最佳数量：100+张（专业级）
```

**图片质量**：
- ✅ 分辨率：512x512 或更高
- ✅ 清晰度：锐利、不模糊
- ✅ 角度：多角度（正面、侧面、背面、3/4）
- ✅ 表情：不同表情（开心、惊讶、生气）
- ✅ 场景：不同背景（可选）
- ❌ 避免：水印、文字、裁剪错误

---

### 3.2 数据集文件夹结构

**标准结构**：
```
training_data/
└─ my_character/              # IP角色名称
   ├─ 10_角色正面.jpg         # 编号_描述.jpg
   ├─ 11_角色侧面.jpg
   ├─ 12_角色背面.jpg
   ├─ 13_角色开心.jpg
   ├─ 14_角色生气.jpg
   ├─ 15_角色跑步.jpg
   ├─ ...
   ├─ caption/
   │  ├─ 10_角色正面.txt      # 对应图片的描述
   │  ├─ 11_角色侧面.txt
   │  └─ ...
   └─ character.json          # 元数据（可选）
```

**命名规则**：
- 文件夹：`数字_触发词` （如 `20_fox_character`）
- 图片：`数字_描述.jpg` （如 `20_fox_front.jpg`）
- 描述：`数字_描述.txt` （如 `20_fox_front.txt`）

---

### 3.3 图片标注（Caption）

**什么是Caption？**
- 每张图片对应一个文本描述
- 告诉AI图片中有什么

**Caption示例**：

```txt
# 图片：可爱的狐狸角色正面
1girl, fox ears, fox tail, orange hair, blue eyes, 
white dress, standing, front view, simple background, 
masterpiece, best quality

# 解释：
1girl          - 一个女孩（角色类型）
fox ears       - 狐狸耳朵
fox tail       - 狐狸尾巴
orange hair    - 橙色头发
blue eyes      - 蓝色眼睛
white dress    - 白色连衣裙
standing       - 站立姿势
front view     - 正面视角
simple background - 简单背景
masterpiece    - 杰作（质量标签）
best quality   - 最佳质量（质量标签）
```

**Caption写作技巧**：

1. **通用格式**：
```
[角色特征], [服装], [姿势], [视角], [背景], [质量标签]
```

2. **包含触发词**：
```
fox_character, 1girl, orange hair, blue eyes, ...
```

3. **描述所有元素**：
```
# 好的Caption
fox_character, 1girl, sitting, reading book, coffee cup, cafe interior

# 差的Caption（太简单）
girl reading
```

4. **使用质量标签**：
```
masterpiece, best quality, ultra-detailed, sharp focus
```

---

### 3.4 自动化工具

#### **工具1：WD Captioner（自动标注）**

```bash
# 安装
pip install wd-captioner

# 使用
python caption_images.py \
  --input_dir training_data/my_character \
  --output_dir training_data/my_character/captions \
  --batch_size 8
```

#### **工具2：BLIP（AI自动描述）**

```python
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch

processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

image = Image.open("training_data/my_character/10_front.jpg").convert("RGB")
inputs = processor(image, return_tensors="pt")
out = model.generate(**inputs)
caption = processor.decode(out[0], skip_special_tokens=True)
print(caption)
# 输出：a cartoon character with orange hair and fox ears
```

---

## ⚙️ 四、训练参数配置

### 4.1 基础参数

```json
{
  "基础模型": "anything-v5-fp16.safetensors",
  "训练数据": "training_data/my_character",
  "输出目录": "output/lora",
  "触发词": "fox_character",
  
  "训练步数": 1000,
  "批次大小": 1,
  "学习率": 0.0001,
  "分辨率": 512,
  
  "LoRA维度": 64,
  "LoRA Alpha": 32,
  "网络权重": 0.7
}
```

---

### 4.2 详细参数说明

#### **训练步数（Steps）**

```
1000步  - 最低要求（快速测试）
2000步  - 推荐（平衡质量和时间）
5000步  - 高质量（精细训练）
10000步 - 专业级（需要大量数据）
```

**计算方式**：
```
总步数 = (图片数量 × 重复次数 × Epoch数) / 批次大小

示例：
30张图片 × 10次重复 × 10 Epoch / 1批次 = 3000步
```

---

#### **学习率（Learning Rate）**

```
1e-3 (0.001)  - 太高，可能不稳定
1e-4 (0.0001) - 推荐（默认）
1e-5          - 太低，训练慢
```

**学习率调度器**：
- `cosine_with_restarts` - 推荐（周期性调整）
- `constant` - 简单但不稳定
- `polynomial` - 平滑下降

---

#### **LoRA维度（Network Dim）**

```
dim=16   - 最小，学习能力弱
dim=32   - 推荐（平衡）
dim=64   - 高质量（需要更多数据）
dim=128  - 最高，可能过拟合
```

**Alpha值**：
```
alpha = dim / 2
例：dim=64, alpha=32
```

---

### 4.3 推荐配置方案

#### **方案A：快速测试（30分钟）**

```json
{
  "max_train_steps": 500,
  "train_batch_size": 1,
  "learning_rate": 1e-4,
  "network_dim": 16,
  "network_alpha": 8,
  "resolution": 512,
  "mixed_precision": "fp16",
  "optimizer_type": "AdamW8bit",
  "lr_scheduler": "cosine_with_restarts"
}
```

**适用场景**：测试数据集质量、快速验证概念

---

#### **方案B：标准训练（2-3小时）⭐ 推荐**

```json
{
  "max_train_steps": 2000,
  "train_batch_size": 1,
  "learning_rate": 1e-4,
  "network_dim": 32,
  "network_alpha": 16,
  "resolution": 512,
  "mixed_precision": "fp16",
  "optimizer_type": "AdamW8bit",
  "lr_scheduler": "cosine_with_restarts",
  "save_every_n_steps": 200,
  "gradient_accumulation_steps": 4
}
```

**适用场景**：大多数IP角色训练

---

#### **方案C：高质量训练（5-8小时）**

```json
{
  "max_train_steps": 5000,
  "train_batch_size": 1,
  "learning_rate": 1e-4,
  "network_dim": 64,
  "network_alpha": 32,
  "resolution": 768,
  "mixed_precision": "bf16",
  "optimizer_type": "DAdaptation",
  "lr_scheduler": "cosine_with_restarts",
  "save_every_n_steps": 500,
  "gradient_accumulation_steps": 8,
  "clip_skip": 2
}
```

**适用场景**：商业项目、高质量要求

---

## 🚀 五、开始训练

### 5.1 使用Kohya_ss GUI

**步骤**：

1. **打开Kohya_ss**
   - 访问：http://localhost:7860

2. **选择训练类型**
   - 点击 "LoRA" 标签

3. **配置参数**
   ```
   Source model: anything-v5-fp16.safetensors
   Image folder: training_data/my_character
   Output folder: output/lora
   Output name: fox_character_lora
   ```

4. **设置训练参数**
   ```
   Batch size: 1
   Epochs: 10
   Learning rate: 0.0001
   Network rank (dim): 32
   Network alpha: 16
   Resolution: 512,512
   ```

5. **开始训练**
   - 点击 "Start Training"
   - 观察进度条和Loss曲线

---

### 5.2 使用命令行

```bash
cd sd-scripts

python train_network.py \
  --pretrained_model_name_or_path "models/v1-5-pruned.ckpt" \
  --train_data_dir "training_data/my_character" \
  --output_dir "output/lora" \
  --output_name "fox_character_lora" \
  --max_train_steps 2000 \
  --train_batch_size 1 \
  --learning_rate 1e-4 \
  --network_dim 32 \
  --network_alpha 16 \
  --resolution 512,512 \
  --mixed_precision fp16 \
  --optimizer_type AdamW8bit \
  --lr_scheduler cosine_with_restarts \
  --save_every_n_steps 200 \
  --gradient_accumulation_steps 4 \
  --clip_skip 2 \
  --seed 42
```

---

### 5.3 使用本项目API

**步骤1：创建训练任务**

```bash
POST /api/v1/lora
{
  "name": "fox_character_lora",
  "base_model": "anything-v5-fp16.safetensors",
  "ip_asset_id": 7,
  "training_params": {
    "max_train_steps": 2000,
    "learning_rate": 1e-4,
    "network_dim": 32,
    "resolution": 512
  }
}
```

**步骤2：启动训练**

```bash
POST /api/v1/lora/1/train
```

**步骤3：监控进度**

```bash
GET /api/v1/lora/1
```

---

## 📊 六、训练监控

### 6.1 关键指标

**Loss（损失值）**：
```
初始Loss: 0.3 - 0.5（高）
正常Loss: 0.05 - 0.15（中）
优秀Loss: < 0.05（低）

Loss曲线应该平滑下降，不应突然上升
```

**训练进度**：
```
0%     - 准备数据
10%    - 开始训练
50%    - 训练中途
90%    - 即将完成
100%   - 训练完成，保存模型
```

---

### 6.2 判断训练质量

**✅ 好的训练**：
- Loss平滑下降
- 最终Loss < 0.1
- 生成的图片质量高
- 角色特征保持良好

**❌ 坏的训练**：
- Loss波动剧烈
- 最终Loss > 0.2
- 生成的图片模糊
- 角色特征丢失（过拟合/欠拟合）

---

### 6.3 常见问题

#### **问题1：过拟合（Overfitting）**

**症状**：
- Loss降得很低（< 0.02）
- 训练图片很完美
- 但生成新图片时质量差

**原因**：
- 训练步数太多
- 数据集太小
- LoRA维度太高

**解决方案**：
```json
{
  "max_train_steps": 1000,  // 减少步数
  "network_dim": 16,        // 降低维度
  "learning_rate": 5e-5     // 降低学习率
}
```

---

#### **问题2：欠拟合（Underfitting）**

**症状**：
- Loss降不下来（> 0.2）
- 生成的图片不像角色
- 角色特征不明显

**原因**：
- 训练步数太少
- 学习率太低
- 数据集质量差

**解决方案**：
```json
{
  "max_train_steps": 3000,  // 增加步数
  "network_dim": 64,        // 增加维度
  "learning_rate": 2e-4     // 提高学习率
}
```

---

#### **问题3：显存不足（OOM）**

**错误信息**：
```
CUDA Out of Memory
Requested X GiB, but only Y GiB available
```

**解决方案**：
```json
{
  "train_batch_size": 1,           // 降低批次大小
  "gradient_accumulation_steps": 8, // 增加梯度累积
  "mixed_precision": "fp16",       // 使用混合精度
  "resolution": 512,512            // 降低分辨率
}
```

---

## 🧪 七、测试训练结果

### 7.1 使用WebUI测试

**步骤**：

1. **打开Stable Diffusion WebUI**
   - 访问：http://localhost:7860

2. **加载LoRA**
   - 点击 "Extra Networks" 按钮
   - 找到你的LoRA模型
   - 点击加载

3. **编写Prompt**
   ```
   fox_character, 1girl, standing, smiling, park background,
   masterpiece, best quality
   ```

4. **生成图片**
   - Steps: 30
   - CFG Scale: 7
   - 点击 "Generate"

5. **调整权重**
   ```
   # 在Prompt中调整权重
   <lora:fox_character_lora:0.5>  // 50%权重
   <lora:fox_character_lora:0.7>  // 70%权重
   <lora:fox_character_lora:1.0>  // 100%权重
   ```

---

### 7.2 使用代码测试

```python
from diffusers import StableDiffusionPipeline
import torch

# 加载基础模型
pipe = StableDiffusionPipeline.from_pretrained(
    "models/anything-v5",
    torch_dtype=torch.float16
)
pipe = pipe.to("cuda")

# 加载LoRA
pipe.load_lora_weights("output/lora/fox_character_lora.safetensors")

# 生成图片
prompt = "fox_character, 1girl, smiling, park, masterpiece, best quality"
image = pipe(prompt, num_inference_steps=30, guidance_scale=7.0).images[0]

# 保存
image.save("test_output.png")
```

---

### 7.3 评估标准

**角色一致性**（最重要）：
```
评分标准：
10/10 - 完美一致，每次都是同一个角色
8/10  - 基本一致，小细节有差异
6/10  - 大致一致，有时不像
4/10  - 经常不像，一致性差
```

**图片质量**：
```
评分标准：
- 清晰度：锐利、不模糊
- 色彩：鲜艳、协调
- 细节：手部、眼睛等细节正确
```

**泛化能力**：
```
测试不同场景：
✅ 室内场景
✅ 室外场景
✅ 不同服装
✅ 不同表情
✅ 不同姿势
```

---

## 🎯 八、实战案例：训练虚拟IP角色

### 8.1 案例背景

**目标**：训练一个治愈系狐狸角色"小白"

**要求**：
- 角色：白色小狐狸拟人化
- 风格：3D卡通、治愈系
- 用途：小红书、抖音内容创作

---

### 8.2 准备数据集

**收集图片**（20张）：
```
training_data/xiaobai_fox/
├─ 10_xiaobai_front_smile.jpg      # 正面微笑
├─ 11_xiaobai_front_happy.jpg      # 正面开心
├─ 12_xiaobai_side_profile.jpg     # 侧面
├─ 13_xiaobai_back_view.jpg        # 背面
├─ 14_xiaobai_3_4_view.jpg         # 3/4视角
├─ 15_xiaobai_sitting.jpg          # 坐姿
├─ 16_xiaobai_standing.jpg         # 站姿
├─ 17_xiaobai_running.jpg          # 跑步
├─ 18_xiaobai_reading.jpg          # 看书
├─ 19_xiaobai_drinking.jpg         # 喝咖啡
├─ 20_xiaobai_cooking.jpg          # 做饭
├─ 21_xiaobai_sleeping.jpg         # 睡觉
├─ 22_xiaobai_surprised.jpg        # 惊讶
├─ 23_xiaobai_angry.jpg            # 生气
├─ 24_xiaobai_crying.jpg           # 哭泣
├─ 25_xiaobai_cafe.jpg             # 咖啡厅场景
├─ 26_xiaobai_park.jpg             # 公园场景
├─ 27_xiaobai_home.jpg             # 家里场景
├─ 28_xiaobai_beach.jpg            # 海滩场景
└─ 29_xiaobai_snow.jpg             # 雪景
```

**编写Caption**：
```txt
# 10_xiaobai_front_smile.txt
xiaobai_fox, 1girl, white fox ears, white fox tail, 
short white hair, blue eyes, cute face, smiling,
pink dress, standing, front view, simple background,
masterpiece, best quality, ultra-detailed, 3d cartoon style

# 15_xiaobai_cafe.txt
xiaobai_fox, 1girl, white fox ears, white fox tail,
sitting at table, coffee cup, reading book,
cafe interior, warm lighting, cozy atmosphere,
masterpiece, best quality, ultra-detailed, 3d cartoon style
```

---

### 8.3 训练配置

```json
{
  "name": "xiaobai_fox_lora",
  "base_model": "anything-v5-fp16.safetensors",
  "training_params": {
    "max_train_steps": 2000,
    "train_batch_size": 1,
    "learning_rate": 1e-4,
    "network_dim": 32,
    "network_alpha": 16,
    "resolution": 512,
    "mixed_precision": "fp16",
    "optimizer_type": "AdamW8bit",
    "lr_scheduler": "cosine_with_restarts",
    "save_every_n_steps": 200,
    "gradient_accumulation_steps": 4,
    "clip_skip": 2,
    "seed": 42
  }
}
```

---

### 8.4 执行训练

```bash
# 使用Kohya_ss GUI或命令行
# 预计时间：2-3小时

# 监控进度
# 0-10%:  准备数据
# 10-90%: 训练进行中（Loss从0.3降到0.08）
# 90-100%: 保存模型
```

---

### 8.5 测试结果

**测试Prompt**：
```
xiaobai_fox, 1girl, standing in park, smiling, 
spring flowers, sunshine, masterpiece, best quality
```

**调整权重**：
```
0.5权重 - 角色特征较弱，但场景多样
0.7权重 - 平衡（推荐）
1.0权重 - 角色特征强，但可能过拟合
```

**评估结果**：
```
角色一致性: 9/10 ✅
图片质量: 8/10 ✅
泛化能力: 8/10 ✅

结论：训练成功，可以投入使用！
```

---

### 8.6 应用到内容创作

**生成日常照片**：
```python
# 每天生成3-5张不同场景的照片
prompts = [
    "xiaobai_fox, 1girl, drinking coffee at cafe, morning light",
    "xiaobai_fox, 1girl, walking in park, cherry blossoms",
    "xiaobai_fox, 1girl, cooking in kitchen, warm atmosphere",
    "xiaobai_fox, 1girl, reading book in library, quiet",
    "xiaobai_fox, 1girl, playing with cat at home, cozy"
]

for prompt in prompts:
    image = generate_with_lora(
        prompt=prompt,
        lora_path="xiaobai_fox_lora.safetensors",
        lora_weight=0.7
    )
    save_image(image)
```

---

## 📈 九、优化建议

### 9.1 提高训练质量

1. **增加数据集**：
   - 从20张增加到50张
   - 覆盖更多角度和场景

2. **优化Caption**：
   - 更详细的描述
   - 包含所有重要元素
   - 使用质量标签

3. **调整参数**：
   - 增加训练步数（2000 → 3000）
   - 增加LoRA维度（32 → 64）
   - 使用更高分辨率（512 → 768）

---

### 9.2 加速训练

1. **使用混合精度**：
   ```json
   {"mixed_precision": "fp16"}  // 或 "bf16"
   ```

2. **降低批次大小**：
   ```json
   {"train_batch_size": 1}
   ```

3. **使用更快的GPU**：
   - RTX 4090比RTX 3060快3-4倍

---

### 9.3 多LoRA组合

**场景**：一个角色，多种服装

**方法**：
```
训练3个LoRA：
- xiaobai_fox_base.safetensors    (角色基础)
- xiaobai_fox_dress.safetensors   (连衣裙)
- xiaobai_fox_casual.safetensors  (休闲装)

使用时切换：
<lora:xiaobai_fox_base:0.7> <lora:xiaobai_fox_dress:0.5>
```

---

## 🔧 十、与本项目集成

### 10.1 当前项目状态

**已实现**：
- ✅ LoRA模型管理（数据库）
- ✅ 训练API接口
- ✅ Celery异步训练任务
- ✅ LoRA权重加载（图像生成时）

**缺失**：
- ❌ 前端训练界面（数据集上传、参数配置）
- ❌ 训练进度实时显示
- ❌ 训练结果测试工具
- ❌ 自动数据集标注

---

### 10.2 集成步骤

**步骤1：安装Kohya_ss**
```powershell
cd E:\idea_workspace\IP-Creator
git clone https://github.com/bmaltais/kohya_ss.git
.\kohya_ss\setup.bat
```

**步骤2：配置路径**
```python
# app/config/settings.py
LORA_MODELS_PATH = "./data/lora_models"
KOHYA_SCRIPT_PATH = "./kohya_ss/train_network.py"
```

**步骤3：使用API训练**
```python
# 通过前端创建训练任务
POST /api/v1/lora
{
  "name": "my_character_lora",
  "base_model": "anything-v5.safetensors",
  "ip_asset_id": 7,
  "training_params": {
    "max_train_steps": 2000,
    "learning_rate": 1e-4,
    "network_dim": 32
  }
}

# 启动训练
POST /api/v1/lora/1/train
```

---

## 📚 十一、学习资源

### 视频教程

1. **LoRA训练完整教程**（中文）
   - B站搜索："LoRA训练教程 Kohya"
   - 推荐：约2小时详细讲解

2. **AI Influencer Workflow**（英文）
   - YouTube搜索："AI Influencer LoRA Training"
   - 推荐：Civitai官方频道

### 文档

1. **Kohya_ss文档**
   - https://github.com/bmaltais/kohya_ss

2. **Civitai教程**
   - https://education.civitai.com/build-an-ai-influencer-with-civitai-com/

### 社区

1. **Civitai**
   - 下载模型、分享LoRA
   - https://civitai.com/

2. **Reddit StableDiffusion**
   - https://www.reddit.com/r/StableDiffusion/

---

## 📋 十二、快速检查清单

训练前：
- [ ] GPU显存 >= 8GB
- [ ] 基础模型已下载
- [ ] 训练数据集 >= 15张图片
- [ ] 每张图片都有Caption
- [ ] 图片分辨率 >= 512x512
- [ ] Kohya_ss已安装

训练中：
- [ ] Loss平滑下降
- [ ] 最终Loss < 0.15
- [ ] 没有OOM错误
- [ ] 训练时间合理

训练后：
- [ ] 模型文件大小合理（50-200MB）
- [ ] 测试生成图片质量高
- [ ] 角色一致性 >= 8/10
- [ ] 在不同场景测试通过

---

## 💡 总结

**LoRA训练核心要点**：

1. **数据集质量 > 一切**
   - 20张高质量图片 > 100张低质量图片

2. **参数平衡**
   - 不要极端值
   - 从推荐配置开始

3. **迭代优化**
   - 第一次训练可能不完美
   - 根据结果调整参数

4. **持续学习**
   - 关注社区最新动态
   - 学习别人的成功案例

**时间投入**：
- 数据集准备：2-4小时
- 训练过程：2-8小时（后台运行）
- 测试优化：1-2小时
- **总计**：5-14小时（可分散到多天）

**成本**：
- 本地GPU：免费（电费约¥5）
- 云GPU：约¥10-50
- **投资回报**：一次训练，无限使用！
