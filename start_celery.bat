@echo off
REM Celery Worker 启动脚本 (Windows)
REM 自动从 celery_worker.py 读取 CELERY_QUEUES 配置，避免手动指定 -Q 参数

cd /d "%~dp0"

echo ==========================================
echo   IP-Creator Celery Worker (Windows)
echo ==========================================
echo.

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 使用 Python 动态读取 CELERY_QUEUES
for /f "delims=" %%i in ('python -c "from celery_worker import CELERY_QUEUES; print(','.join(CELERY_QUEUES))"') do set QUEUES=%%i

if "%QUEUES%"=="" (
    echo ERROR: 无法从 celery_worker.py 读取 CELERY_QUEUES
    pause
    exit /b 1
)

echo 启动 Celery Worker...
echo 监听队列: %QUEUES%
echo.

REM 启动 Celery Worker，使用读取到的队列配置
celery -A celery_worker.celery_app worker --loglevel=info --pool=solo -Q %QUEUES%

pause
