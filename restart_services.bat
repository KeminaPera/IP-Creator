@echo off
REM IP-Creator Service Restart Script
REM This script stops and restarts all IP-Creator services

echo ============================================================
echo   IP-Creator Service Restart
echo ============================================================
echo.

echo Step 1: Stopping existing services...
echo.
echo Please manually close the following windows:
echo   - IP-Creator Backend (Port 8000)
echo   - IP-Creator Celery (Worker)
echo   - IP-Creator Frontend (Port 5173)
echo.
echo Press any key after closing them...
pause >nul

echo.
echo Step 2: Checking prerequisites...
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
echo [OK] Python: 
python --version

REM Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)
echo [OK] Node.js: 
node --version

REM Check Redis
redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Redis is not running locally
    echo       Make sure remote Redis is accessible or start local Redis
) else (
    echo [OK] Redis: Running
)

echo.
echo Step 3: Starting services...
echo.

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
start "IP-Creator Celery" cmd /k "call venv\Scripts\activate.bat && celery -A celery_worker.celery_app worker --loglevel=info --pool=solo -Q celery,story_generation,image_generation,video_generation,training"

timeout /t 3 /nobreak >nul

echo ============================================================
echo   Starting Frontend (Port 5173)
echo ============================================================
echo.
start "IP-Creator Frontend" cmd /k "cd frontend-vue && npm run dev"

echo.
echo ============================================================
echo   IP-Creator services are starting!
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
echo Recent Code Review Fixes Applied:
echo   [SECURITY] Startup key validation
echo   [SECURITY] Dynamic encryption salt
echo   [QUALITY] Exception handling (21 fixes)
echo   [QUALITY] Debug log conditional output
echo   [A11Y] Image alt attributes
echo   [I18N] Error message internationalization
echo.
echo Press any key to exit this window...
echo (Services will continue running in separate windows)
pause >nul
