# Git 推送指南

## ✅ 项目已准备就绪

项目已完成初始化和首次提交，现在可以推送到远程仓库。

---

## 📋 提交摘要

**提交哈希：** `e9f7a16`
**提交信息：** `feat: Initial commit - IP Creator Full-Stack Application`
**文件数量：** 211 个文件
**仓库大小：** 6.54 MiB

---

## 🚀 推送到远程仓库

### **选项 1：推送到 GitHub**

```bash
# 1. 在 GitHub 上创建新仓库（不要初始化 README、.gitignore 或 license）

# 2. 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/ip-creator.git

# 3. 推送到 GitHub
git branch -M main
git push -u origin main
```

### **选项 2：推送到 GitLab**

```bash
# 1. 在 GitLab 上创建新项目

# 2. 添加远程仓库
git remote add origin https://gitlab.com/YOUR_USERNAME/ip-creator.git

# 3. 推送到 GitLab
git branch -M main
git push -u origin main
```

### **选项 3：推送到 Gitee（码云）**

```bash
# 1. 在 Gitee 上创建新仓库

# 2. 添加远程仓库
git remote add origin https://gitee.com/YOUR_USERNAME/ip-creator.git

# 3. 推送到 Gitee
git branch -M main
git push -u origin main
```

### **选项 4：推送到私有 Git 服务器**

```bash
# 1. 在服务器上创建裸仓库
ssh user@your-server.com
mkdir -p /path/to/repos/ip-creator.git
cd /path/to/repos/ip-creator.git
git init --bare
exit

# 2. 添加远程仓库
git remote add origin ssh://user@your-server.com/path/to/repos/ip-creator.git

# 3. 推送
git branch -M main
git push -u origin main
```

---

## 🔐 使用 SSH 推送（推荐）

### **生成 SSH 密钥（如果没有）**

```bash
# Windows PowerShell
ssh-keygen -t ed25519 -C "your_email@example.com"

# 或使用 RSA
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

### **添加 SSH 密钥到 Git 服务**

```bash
# 复制公钥
cat ~/.ssh/id_ed25519.pub
# 或
cat ~/.ssh/id_rsa.pub
```

将输出的内容添加到你的 Git 服务（GitHub/GitLab/Gitee）的 SSH Keys 设置中。

### **使用 SSH URL 推送**

```bash
# GitHub
git remote add origin git@github.com:YOUR_USERNAME/ip-creator.git

# GitLab
git remote add origin git@gitlab.com:YOUR_USERNAME/ip-creator.git

# Gitee
git remote add origin git@gitee.com:YOUR_USERNAME/ip-creator.git

# 推送
git branch -M main
git push -u origin main
```

---

## 📝 推送前检查清单

### ✅ **已完成**
- [x] 初始化 Git 仓库
- [x] 配置 .gitignore
- [x] 添加所有文件
- [x] 创建初始提交
- [x] 删除无用文件
- [x] 整理文档到 docs/ 目录

### ⚠️ **推送前检查**
- [ ] 确认没有提交敏感信息（.env 文件、密码、API Keys）
- [ ] 确认 .gitignore 配置正确
- [ ] 确认 data/ 目录中的测试数据是否需要提交
- [ ] 确认 logs/ 目录已被忽略

### 🔍 **检查敏感文件**

```bash
# 检查是否包含 .env 文件
git ls-files | grep -E "\.env$|\.db$|\.log$"

# 检查提交的文件列表
git show --name-only --oneline HEAD

# 查看提交详情
git log -1 --stat
```

---

## 🗂️ 项目结构

```
ip-creator/
├── .env.example              # 环境变量示例
├── .gitignore                # Git 忽略规则
├── API_REFERENCE.md          # API 参考文档
├── Dockerfile                # Docker 配置
├── LORA_TRAINING_GUIDE.md    # LoRA 训练指南
├── README.md                 # 项目说明
├── app/                      # 后端代码
│   ├── api/                  # API 路由
│   ├── config/               # 配置
│   ├── core/                 # 核心逻辑
│   ├── models/               # 数据模型
│   ├── services/             # 业务服务
│   └── tasks/                # Celery 任务
├── celery_worker.py          # Celery 工作进程
├── data/                     # 数据目录
├── docs/                     # 文档
├── frontend-vue/             # 前端代码
│   ├── src/
│   │   ├── api/              # API 调用
│   │   ├── components/       # Vue 组件
│   │   ├── i18n/             # 国际化
│   │   ├── views/            # 页面视图
│   │   └── ...
│   └── public/               # 静态资源
├── migrations/               # 数据库迁移
├── sql/                      # SQL 脚本
├── requirements.txt          # Python 依赖
└── ...
```

---

## 📌 后续操作

### **创建开发分支**

```bash
# 创建开发分支
git checkout -b develop

# 推送开发分支
git push -u origin develop
```

### **创建标签（可选）**

```bash
# 创建版本标签
git tag -a v1.0.0 -m "Initial release"

# 推送标签
git push origin v1.0.0
```

### **配置分支保护（在 Git 服务上）**

- 保护 `main` 分支
- 要求 Pull Request
- 要求代码审查
- 要求 CI 检查通过

---

## 🔧 常用 Git 命令

```bash
# 查看状态
git status

# 查看提交历史
git log --oneline --graph --all

# 查看变更
git diff

# 添加文件
git add <file>

# 提交变更
git commit -m "message"

# 推送到远程
git push

# 拉取更新
git pull

# 创建新分支
git checkout -b feature/xxx

# 合并分支
git merge feature/xxx
```

---

## ⚠️ 注意事项

1. **永远不要提交敏感信息**
   - `.env` 文件（已忽略）
   - 数据库文件（已忽略）
   - 日志文件（已忽略）
   - API Keys、密码等

2. **大文件处理**
   - 如果 data/ 目录中的文件过大，考虑使用 Git LFS
   - 图片、视频等多媒体文件建议使用 Git LFS

3. **定期提交**
   - 完成一个功能后立即提交
   - 提交信息要清晰明了

4. **使用分支**
   - main 分支保持稳定
   - 新功能在独立分支开发
   - 使用 Pull Request 合并

---

## 📞 需要帮助？

如果推送过程中遇到问题，可以：
1. 检查网络连接
2. 验证 Git 凭据
3. 检查远程仓库 URL
4. 查看 Git 错误日志

```bash
# 查看详细错误
GIT_CURL_VERBOSE=1 git push origin main
```

---

**祝推送顺利！🎉**
