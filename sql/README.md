# 数据库脚本说明

本目录包含项目的所有数据库架构和迁移脚本。

---

## 📁 目录结构

```
sql/
├── README.md                           # 本文件
├── schema_complete.sql                 # 完整数据库架构（最新版 v2.0）
├── seed_data.sql                       # 种子数据（LLM 供应商和模型）
├── init_database.py                    # 数据库初始化脚本（建表+种子数据+管理员）
├── init_admin.py                       # 管理员账号初始化脚本
├── init_system_settings.py             # 系统设置初始化脚本
├── export_database.py                  # 数据库导出工具
├── seed_lora_data.py                   # LoRA测试数据种子脚本
├── apply_migration_010.py              # 应用迁移010的脚本
└── migrations/                         # 迁移脚本
    ├── 004_create_generated_contents.sql   # 内容库表创建
    ├── 005_add_performance_indexes.sql     # 性能索引优化
    ├── 006_create_training_datasets.sql    # 训练数据集表
    ├── 007_add_quality_reports.py          # 质量报告表
    ├── 007_create_test_images_and_checkpoints.sql
    ├── 008_add_clip_consistency.py         # CLIP一致性字段
    ├── 008_extend_lora_models.sql          # LoRA模型扩展
    ├── 009_create_ip_feature_library.sql   # IP特征库
    └── 010_add_training_diagnosis.sql      # 训练诊断字段
```

---

## 📄 文件说明

### **1. schema_complete.sql** ⭐

**版本：** 2.0  
**更新日期：** 2026-05-05  
**用途：** 完整的数据库架构定义

**包含的表：**
1. `users` - 用户管理
2. `llm_providers` - LLM 供应商配置
3. `llm_models` - LLM 模型配置
4. `llm_configs` - LLM 通道配置
5. `ip_assets` - IP 资产管理
6. `ip_reference_images` - IP 参考图片
7. `lora_models` - LoRA 模型训练
8. `task_records` - 任务记录
9. `generated_contents` - 生成内容库
10. `system_settings` - 系统设置

**使用方法：**
```bash
# 方式1：使用SQL脚本
sqlite3 data/ip_creator.db < sql/schema_complete.sql

# 方式2：使用Python脚本（推荐，包含完整初始化流程）
python sql/init_database.py
```

---

### **2. seed_data.sql**

**用途：** 插入初始数据（种子数据）

**包含的数据：**
- 11 个 LLM 供应商配置
  - OpenAI, Anthropic, Google Gemini, DeepSeek
  - 智谱 AI, 通义千问, 豆包, 文心一言
  - 讯飞星火, Ollama, LM Studio
- 预配置的模型列表

**使用方法：**
```bash
# 在架构创建后执行
sqlite3 data/ip_creator.db < sql/seed_data.sql

# 或使用Python脚本一键初始化（推荐）
python sql/init_database.py
```

---

### **3. Python 初始化脚本**

#### **init_database.py** ⭐
- **用途：** 完整的数据库初始化脚本
- **执行步骤：**
  1. 执行 `schema_complete.sql` 创建所有表
  2. 执行 `seed_data.sql` 插入初始数据
  3. 创建默认管理员账号（admin/admin123）
- **使用方法：** `python sql/init_database.py`

#### **init_admin.py**
- **用途：** 单独创建或重置管理员账号
- **使用方法：** `python sql/init_admin.py`

#### **init_system_settings.py**
- **用途：** 初始化系统设置（4个分类，14条设置）
- **使用方法：** `python sql/init_system_settings.py`

#### **export_database.py**
- **用途：** 导出数据库为JSON格式
- **使用方法：** `python sql/export_database.py`

#### **seed_lora_data.py**
- **用途：** 插入LoRA训练测试数据
- **使用方法：** `python sql/seed_lora_data.py`

#### **apply_migration_010.py**
- **用途：** 应用数据库迁移010
- **使用方法：** `python sql/apply_migration_010.py`

### **4. migrations/ 目录**

包含数据库迁移脚本，用于从旧版本升级到新版本。

#### **004_create_generated_contents.sql**
- **日期：** 2026-05-05
- **说明：** 创建生成内容库表
- **影响：** 新增 `generated_contents` 表
- **注意：** 已包含在 `schema_complete.sql` 中

#### **005_add_performance_indexes.sql**
- **日期：** 2026-05-06
- **说明：** 添加性能优化索引
- **影响：** 为所有表添加复合索引
- **注意：** 已包含在 `schema_complete.sql` 中

---

## 🛠️ 数据库初始化工具

### **推荐方式：一键初始化**

```bash
# 完整的数据库初始化（建表+种子数据+管理员）
python sql/init_database.py
```

### **分步初始化**

```bash
# 1. 创建表结构
sqlite3 data/ip_creator.db < sql/schema_complete.sql

# 2. 插入种子数据
sqlite3 data/ip_creator.db < sql/seed_data.sql

# 3. 创建管理员
python sql/init_admin.py

# 4. 初始化系统设置
python sql/init_system_settings.py
```

---

## 📝 重要说明

### **schema.sql vs schema_complete.sql**

- `schema.sql` - **已过时**，早期版本
- `schema_complete.sql` - **当前使用**，包含所有最新的表结构和索引

**建议：** 始终使用 `schema_complete.sql`

### **迁移脚本的使用场景**

1. **新项目部署：** 直接运行 `schema_complete.sql`，无需执行迁移脚本
2. **已有项目升级：** 按顺序执行 `migrations/` 中的脚本
3. **开发环境：** 使用 `init_database.py` 一键初始化

---

## 🔧 常用 SQL 命令

### **查看表列表**
```sql
.tables
```

### **查看表结构**
```sql
.schema table_name
```

### **导出数据**
```bash
sqlite3 data/ip_creator.db ".dump" > backup.sql
```

### **导入数据**
```bash
sqlite3 data/ip_creator.db < backup.sql
```

---

## 📊 数据库版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-04-30 | 初始架构（schema.sql）|
| v2.0 | 2026-05-05 | 完整架构（schema_complete.sql）|
| v2.1 | 2026-05-06 | 添加性能索引 |

---

## ⚠️ 注意事项

1. **备份数据：** 在执行任何迁移前，请备份数据库
2. **测试环境：** 先在测试环境验证迁移脚本
3. **版本控制：** 所有数据库变更都应通过迁移脚本管理
4. **文档更新：** 修改架构后，同步更新本文档

---

## 📞 问题排查

### **常见问题**

**Q: 应该使用哪个架构文件？**  
A: 始终使用 `schema_complete.sql`

**Q: 迁移脚本是否必须执行？**  
A: 如果是新项目，不需要。如果是升级旧项目，需要按顺序执行。

**Q: 如何查看当前数据库版本？**  
A: 检查是否存在 `generated_contents` 表，如果存在则是 v2.0+

---

**最后更新：** 2026-05-10
