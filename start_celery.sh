#!/usr/bin/env bash
# IP-Creator Celery Worker 启动脚本 (macOS / Linux)
# 必须显式 -Q 监听全部自定义队列, 否则 task_routes 路由后的任务无人消费
# 详见 celery_worker.py 中 task_routes 配置

set -e
cd "$(dirname "$0")"

# 队列列表来自 celery_worker.py 中的 CELERY_QUEUES (SSOT, 单一可信源)
# 修改队列只需改 celery_worker.py, 此处自动同步
if [ -d "venv" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

CELERY_QUEUES="$(python -c 'from celery_worker import CELERY_QUEUES; print(",".join(CELERY_QUEUES))')"
if [ -z "$CELERY_QUEUES" ]; then
    echo "❌ 无法从 celery_worker.py 读取 CELERY_QUEUES, 请检查该文件是否定义了该常量" >&2
    exit 1
fi
CELERY_POOL="${CELERY_POOL:-solo}"
CELERY_LOGLEVEL="${CELERY_LOGLEVEL:-info}"
CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-1}"

# 日志目录
mkdir -p logs

echo "=========================================="
echo "  IP-Creator Celery Worker"
echo "=========================================="
echo "  Queues : $CELERY_QUEUES"
echo "  Pool   : $CELERY_POOL"
echo "  Level  : $CELERY_LOGLEVEL"
echo "=========================================="

exec celery -A celery_worker.celery_app worker \
    --loglevel="$CELERY_LOGLEVEL" \
    --pool="$CELERY_POOL" \
    --concurrency="$CELERY_CONCURRENCY" \
    -Q "$CELERY_QUEUES"
