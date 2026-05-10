#!/usr/bin/env python3
"""
Startup script for IP Creator application.

This script initializes the application and starts both
the FastAPI server and provides instructions for Celery.
"""
import subprocess
import sys
import os
from pathlib import Path


def check_requirements():
    """Check if all required services are available."""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version}")
    
    # Check if .env exists
    if not Path(".env").exists():
        print("⚠️  .env file not found. Creating from .env.example...")
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file - please update with your configuration")
        else:
            print("❌ .env.example not found")
            sys.exit(1)
    
    # Check required directories
    dirs = ["data", "data/ip_assets", "data/lora_models", "data/videos", "data/models", "logs"]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print("✅ All directories created")


def start_server():
    """Start the FastAPI server."""
    print("\n🚀 Starting IP Creator server...")
    print("📖 API Documentation: http://localhost:8000/api/docs")
    print("💚 Health Check: http://localhost:8000/api/health\n")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")


def print_celery_instructions():
    """Print instructions for starting Celery worker."""
    print("\n" + "="*60)
    print("📋 IMPORTANT: Start Celery worker in a separate terminal:")
    print("="*60)
    print("\ncelery -A celery_worker.celery_app worker --loglevel=info\n")
    print("="*60)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎨 IP Creator - AI Cartoon IP Video Generation System")
    print("="*60 + "\n")
    
    check_requirements()
    print_celery_instructions()
    start_server()
