@echo off
REM IP-Creator Quick Start Script for Windows
REM This script initializes the database and starts all services

echo ============================================================
echo   IP-Creator Quick Start
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
python --version
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [2/4] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    echo [2/4] Activating virtual environment...
    call venv\Scripts\activate.bat
)
echo.

REM Initialize database if not exists
if not exist "data\ip_creator.db" (
    echo [3/4] Initializing database...
    python init_database.py
    if %errorlevel% neq 0 (
        echo ERROR: Database initialization failed
        pause
        exit /b 1
    )
) else (
    echo [3/4] Database already initialized
)
echo.

echo [4/4] Starting services...
echo.

REM ✅ IP-Adapter 模式：original / faceid / faceid-plus
REM    original    - CLIP 图像特征，兼容 LoRA
REM    faceid      - insightface 512 维人脸特征（推荐）
REM    faceid-plus - insightface + CLIP ViT-H/14（最高质量，需 ~3.94 GB 模型）
set IP_ADAPTER_MODE=faceid

echo ============================================================
echo   Starting Backend API (Port 8000)
echo ============================================================
echo.
start "IP-Creator Backend" cmd /k "call venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo ============================================================
echo   Starting Celery Worker
echo ============================================================
echo.
:: SSOT: 使用 PowerShell 动态读取 CELERY_QUEUES 常量
start "IP-Creator Celery" cmd /k "call venv\Scripts\activate.bat && powershell -Command \"$$queues = python -c 'from celery_worker import CELERY_QUEUES; print(\",\".join(CELERY_QUEUES))'; celery -A celery_worker.celery_app worker --loglevel=info --pool=solo -Q $$queues\""

timeout /t 3 /nobreak >nul

echo ============================================================
echo   Starting Frontend (Port 5173)
echo ============================================================
echo.
start "IP-Creator Frontend" cmd /k "cd frontend-vue && npm run dev"

echo.
echo ============================================================
echo   IP-Creator is starting!
echo ============================================================
echo.
echo Services:
echo   - Backend API:  http://localhost:8000
echo   - API Docs:     http://localhost:8000/docs
echo   - Frontend:     http://localhost:5173
echo.
echo Login Credentials:
echo   - Username: admin
echo   - Password: admin123
echo.
echo IMPORTANT: Change the admin password after first login!
echo.
echo Press any key to exit this window...
echo (Services will continue running in separate windows)
pause >nul
