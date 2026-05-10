# 执行计划快速参考指南

**更新日期：** 2026-05-10  
**完整计划：** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

---

## 🎯 项目目标

实现完整的 IP 孵化流程：
1. ✅ LoRA 训练完全可用（非模拟）
2. ✅ IP-Adapter 真实集成
3. ✅ 训练质量可评估
4. ✅ 用户体验流畅

---

## 📅 关键时间节点

| 里程碑 | 日期 | 目标 |
|--------|------|------|
| **阶段一完成** | 2026-05-24 | 数据集管理可用 |
| **阶段二完成** | 2026-06-07 | Kohya 真实训练可用 |
| **阶段三完成** | 2026-06-21 | 质量评估体系可用 |
| **阶段四完成** | 2026-06-28 | IP-Adapter 增强完成 |
| **项目完成** | 2026-06-28 | 全部功能可用 |

---

## 🔴 当前优先级任务（Week 1: 5月11日-17日）

### **必须完成（P0）**

```
✅ 任务 1.1: 数据库设计与迁移（4小时）
   - 创建 3 个迁移脚本
   - 5 个新表 + 1 个表扩展

✅ 任务 1.2: SQLAlchemy 模型定义（4小时）
   - 4 个新模型文件
   - 修改 1 个现有模型

✅ 任务 1.3: Pydantic Schemas（3小时）
   - 3 个 schema 文件

✅ 任务 1.4: DatasetManager 核心服务（8小时）
   - 上传功能
   - 质量检查
   - 自动去重
   - 数据集验证
```

**本周总工时：** 19 小时  
**检查日期：** 2026-05-17（周日）

---

## 📋 每周检查清单

### **周日检查（30 分钟）**

```
1. [ ] 运行所有单元测试
   命令：pytest tests/ -v
   目标：通过率 100%

2. [ ] 检查代码规范
   命令：flake8 app/
   目标：0 错误

3. [ ] 更新进度跟踪表
   文件：IMPLEMENTATION_PLAN.md 中的进度表

4. [ ] 记录本周完成的任务

5. [ ] 记录遇到的问题和解决方案

6. [ ] 确认下周计划
```

---

## 🚦 任务状态说明

| 状态 | 图标 | 含义 |
|------|------|------|
| 待开始 | ⏳ | 还未开始 |
| 进行中 | 🔄 | 正在开发 |
| 已完成 | ✅ | 开发完成，测试通过 |
| 阻塞中 | 🚫 | 遇到问题无法继续 |
| 已取消 | ❌ | 不再需要 |

---

## 📊 快速进度跟踪

### **阶段进度**

```
阶段一：数据集管理 [████████████░░░░░░░░] 60% (Week 1-2)
阶段二：Kohya 集成  [░░░░░░░░░░░░░░░░░░░░] 0%  (Week 3-4)
阶段三：质量评估    [░░░░░░░░░░░░░░░░░░░░] 0%  (Week 5-6)
阶段四：IP-Adapter  [░░░░░░░░░░░░░░░░░░░░] 0%  (Week 7)
```

### **本周任务进度**（Week 1）

```
任务 1.1: 数据库迁移     [ ] [ ] [ ] [ ] [ ]  0/5
任务 1.2: 模型定义       [ ] [ ] [ ] [ ] [ ]  0/5
任务 1.3: Schemas        [ ] [ ] [ ]          0/3
任务 1.4: DatasetManager [ ] [ ] [ ] [ ] [ ]  0/5
```

---

## ⚠️ 常见问题快速处理

### **问题 1：数据库迁移失败**

```bash
# 检查迁移脚本
cat sql/migrations/006_create_training_datasets.sql

# 手动执行迁移
sqlite3 data/ip_creator.db < sql/migrations/006_create_training_datasets.sql

# 验证表创建
sqlite3 data/ip_creator.db ".tables"
```

### **问题 2：测试失败**

```bash
# 运行单个测试文件
pytest tests/test_dataset_manager.py -v

# 运行单个测试函数
pytest tests/test_dataset_manager.py::test_upload_dataset -v

# 查看详细信息
pytest tests/test_dataset_manager.py -v -s
```

### **问题 3：Kohya 未找到**

```bash
# 检查环境变量
echo $KOHYA_PATH

# 检查常见路径
ls ~/kohya_ss/train_network.py
ls /opt/kohya_ss/train_network.py

# 设置环境变量
export KOHYA_PATH=~/kohya_ss
```

---

## 📁 关键文件位置

### **后端核心文件**

```
app/
├── models/
│   ├── training_dataset.py      # 数据集模型
│   ├── dataset_image.py         # 数据集图片模型
│   ├── test_image.py            # 测试图片模型
│   └── training_checkpoint.py   # 检查点模型
├── services/
│   ├── dataset_manager.py       # 数据集管理服务
│   ├── kohya_integration.py     # Kohya 集成
│   ├── quality_assessor.py      # 质量评估
│   └── feature_extractor.py     # 特征提取
└── api/v1/
    ├── dataset_router.py        # 数据集 API
    └── ws_router.py             # WebSocket
```

### **前端核心文件**

```
frontend-vue/src/
├── views/
│   ├── DatasetManagement.vue    # 数据集管理
│   ├── TrainingMonitor.vue      # 训练监控
│   └── QualityReport.vue        # 质量报告
├── components/
│   ├── dataset/                 # 数据集组件
│   └── training/                # 训练组件
└── api/
    └── dataset.js               # 数据集 API 客户端
```

---

## 🎯 每日工作建议

### **工作日（每天 2-3 小时）**

```
Day 1-2: 数据库和模型（任务 1.1-1.2）
Day 3:   Schemas（任务 1.3）
Day 4-5: DatasetManager 核心功能（任务 1.4）
Day 6:   单元测试和修复 bug
Day 7:   周检查和文档更新
```

### **工作流**

```
1. 拉取最新代码
   git pull origin feature/optimization

2. 创建功能分支
   git checkout -b feature/dataset-management

3. 开发功能
   - 编写代码
   - 编写测试
   - 本地测试

4. 提交代码
   git add .
   git commit -m "feat: implement dataset upload"
   git push origin feature/dataset-management

5. 创建 Pull Request
   - 描述变更内容
   - 附上测试结果
   - 请求代码审查

6. 合并到主分支
   - 审查通过
   - 解决冲突
   - 合并
```

---

## 📞 需要帮助？

### **查看完整计划**
- 文件：`IMPLEMENTATION_PLAN.md`
- 内容：详细的任务描述、验收标准、交付物

### **查看设计文档**
- 文件：`LORA_IPADAPTER_DESIGN.md`
- 内容：技术架构、模块设计、数据库设计

### **查看优化分析**
- 文件：`OPTIMIZATION_ANALYSIS.md`
- 内容：项目分析、优化建议、优先级矩阵

---

## ✅ 成功标准

### **Week 1 成功标准**

```
✅ 数据库迁移脚本可执行
✅ 所有模型定义完整
✅ DatasetManager 基础功能完成
✅ 单元测试覆盖率 > 70%
✅ 代码审查通过
```

### **项目成功标准**

```
✅ 数据集上传成功率 > 95%
✅ 训练成功率 > 90%
✅ 质量评估准确率 > 85%
✅ IP 一致性评分 > 85
✅ 用户满意度 > 4.5/5
```

---

## 🚀 立即开始

### **第一步：准备开发环境**（30 分钟）

```bash
# 1. 确认当前分支
git branch
# 应该在：feature/optimization

# 2. 拉取最新代码
git pull origin feature/optimization

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行现有测试
pytest tests/ -v

# 5. 确认环境正常
python -c "from app.config.database import async_session_factory; print('OK')"
```

### **第二步：开始任务 1.1**（4 小时）

```bash
# 1. 创建功能分支
git checkout -b feature/database-migrations

# 2. 创建迁移脚本
# 文件：sql/migrations/006_create_training_datasets.sql

# 3. 测试迁移
sqlite3 data/ip_creator.db < sql/migrations/006_create_training_datasets.sql

# 4. 验证表
sqlite3 data/ip_creator.db ".tables"

# 5. 提交
git add sql/migrations/006_create_training_datasets.sql
git commit -m "feat: add training datasets migration"
git push origin feature/database-migrations
```

---

**准备好了吗？让我们开始执行 Week 1 的任务！** 💪

**下一个检查点：** 2026-05-17（周日）  
**目标：** 完成 Week 1 所有任务
