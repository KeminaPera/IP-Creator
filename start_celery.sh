#!/bin/bash
# Celery Worker 启动脚本
# 自动从 celery_worker.py 读取 CELERY_QUEUES 配置，避免手动指定 -Q 参数

set -e

# 设置macOS环境变量，解决multiprocessing.Value权限问题
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export PYTORCH_ENABLE_MPS_FALLBACK=1

cd "$(dirname "$0")"

# 激活虚拟环境
source venv/bin/activate

# 从 celery_worker.py 动态读取 CELERY_QUEUES
QUEUES=$(python3 -c "
from celery_worker import CELERY_QUEUES
print(','.join(CELERY_QUEUES))
")

echo "🚀 启动 Celery Worker..."
echo "📋 监听队列: $QUEUES"

# 启动 Celery Worker，使用solo模式避免macOS权限问题
exec celery -A celery_worker worker \
    --loglevel=info \
    --pool=solo \
    -Q "$QUEUES" \
    -n worker1@%h
