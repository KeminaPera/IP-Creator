# Docker 部署指南

本文档介绍如何使用 Docker 部署 IP Creator 系统。

---

## 📋 前提条件

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **NVIDIA GPU** (可选，用于 AI 生成任务)
- **NVIDIA Container Toolkit** (如果使用 GPU)

---

## 🚀 快速开始

### **1. 构建并启动服务**

```bash
# 构建镜像并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### **2. 初始化数据库**

```bash
# 进入 web 容器
docker-compose exec web bash

# 运行数据库初始化
python init_database.py

# 退出容器
exit
```

### **3. 访问应用**

- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Redis**: localhost:6379

---

## 🔧 配置选项

### **环境变量**

创建 `.env` 文件（或编辑现有文件）：

```env
# Secret Key (IMPORTANT: Change in production!)
SECRET_KEY=your-super-secret-key-here

# Environment
ENVIRONMENT=production

# Database (default is fine)
DATABASE_URL=sqlite+aiosqlite:///./data/ip_creator.db

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

### **GPU 支持**

如果使用 NVIDIA GPU 进行 AI 生成，编辑 `docker-compose.yml`：

```yaml
celery_worker:
  # ... 其他配置 ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

**取消注释** celery_worker 服务中的 GPU 配置部分。

---

## 📦 服务说明

### **服务架构**

```
┌─────────────────┐
│   Web (FastAPI) │ :8000
│   - API Server  │
│   - Frontend    │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  Redis   │ :6379
    │  Queue   │
    └────┬─────┘
         │
    ┌────▼──────────┐
    │ Celery Worker │
    │ - AI Tasks    │
    │ - GPU (opt)   │
    └───────────────┘
```

### **服务列表**

| 服务 | 端口 | 说明 | 必需 |
|------|------|------|------|
| **web** | 8000 | FastAPI 后端 + 前端静态文件 | ✅ |
| **celery_worker** | - | 异步任务处理（AI 生成）| ✅ |
| **redis** | 6379 | 消息队列和缓存 | ✅ |
| **nginx** | 80, 443 | 反向代理（可选）| ⭕ |

---

## 🛠️ 常用命令

### **启动/停止**

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart web

# 停止并删除所有数据卷（⚠️ 危险操作）
docker-compose down -v
```

### **日志查看**

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f web
docker-compose logs -f celery_worker

# 查看最近 100 行日志
docker-compose logs --tail=100 web
```

### **进入容器**

```bash
# 进入 web 容器
docker-compose exec web bash

# 进入 celery worker 容器
docker-compose exec celery_worker bash

# 进入 redis 容器
docker-compose exec redis redis-cli
```

### **数据库操作**

```bash
# 备份数据库
docker-compose exec web cp /app/data/ip_creator.db /app/data/backup_$(date +%Y%m%d).db

# 导出备份到主机
docker-compose cp web:/app/data/backup_20260510.db ./backup.db

# 运行数据库初始化
docker-compose exec web python init_database.py
```

---

## 📊 数据持久化

### **Docker Volumes**

数据通过 Docker volumes 持久化：

- `app_data` - 数据库和生成的内容
- `app_logs` - 应用日志
- `redis_data` - Redis 数据

### **查看数据卷**

```bash
# 列出所有数据卷
docker volume ls | grep ip-creator

# 查看数据卷详情
docker volume inspect ip-creator_app_data
```

### **备份数据**

```bash
# 备份数据卷
docker run --rm \
  -v ip-creator_app_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/app_data_backup.tar.gz -C /data .

# 恢复数据卷
docker run --rm \
  -v ip-creator_app_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/app_data_backup.tar.gz -C /data
```

---

## 🔍 故障排查

### **服务无法启动**

```bash
# 查看详细日志
docker-compose logs web

# 检查端口占用
netstat -tulpn | grep 8000

# 重新构建镜像
docker-compose build --no-cache
```

### **Celery Worker 无法连接**

```bash
# 检查 Redis 是否运行
docker-compose exec redis redis-cli ping

# 检查网络连接
docker-compose exec web ping redis

# 重启 Redis
docker-compose restart redis
```

### **数据库初始化失败**

```bash
# 检查数据库文件权限
docker-compose exec web ls -la /app/data/

# 手动创建目录
docker-compose exec web mkdir -p /app/data
docker-compose exec web chmod 755 /app/data
```

---

## 🎯 生产部署建议

### **1. 安全措施**

- ✅ 修改 `SECRET_KEY` 为强随机字符串
- ✅ 使用 HTTPS（通过 nginx + SSL 证书）
- ✅ 限制 Redis 端口不暴露到公网
- ✅ 定期更新依赖和基础镜像
- ✅ 启用防火墙规则

### **2. 性能优化**

- ✅ 启用 GPU 支持（如果有）
- ✅ 增加 Celery worker 数量
- ✅ 配置 Redis 内存限制
- ✅ 使用 Docker Swarm 或 Kubernetes 扩展

### **3. 监控和日志**

- ✅ 配置日志轮转
- ✅ 使用 Prometheus + Grafana 监控
- ✅ 设置健康检查告警
- ✅ 定期备份数据

---

## 📝 Nginx 反向代理（可选）

如果需要 nginx 作为反向代理，编辑 `docker-compose.yml`：

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - web
    networks:
      - ip_creator_network
    restart: unless-stopped
```

然后启动：

```bash
docker-compose up -d nginx
```

---

## 🔄 更新和升级

### **更新应用代码**

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 检查服务状态
docker-compose ps
```

### **更新依赖**

```bash
# 进入 web 容器
docker-compose exec web bash

# 更新 Python 依赖
pip install -r requirements.txt --upgrade

# 退出并重启
exit
docker-compose restart web
```

---

## ⚠️ 注意事项

1. **数据备份**：定期备份 `app_data` 数据卷
2. **密钥管理**：不要使用默认的 `SECRET_KEY`
3. **GPU 驱动**：确保主机已安装 NVIDIA 驱动
4. **端口冲突**：确保 8000 和 6379 端口未被占用
5. **磁盘空间**：AI 生成内容可能占用大量磁盘空间

---

## 📞 获取帮助

- **查看日志**：`docker-compose logs -f`
- **进入容器调试**：`docker-compose exec web bash`
- **检查服务状态**：`docker-compose ps`
- **重启服务**：`docker-compose restart <service>`

---

**最后更新：** 2026-05-10
