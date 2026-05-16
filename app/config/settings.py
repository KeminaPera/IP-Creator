"""
IP Creator - Configurable Multi-LLM Localized AI Cartoon IP Video Generation System

Configuration management module with environment variable support.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic for validation and type safety.
    """
    
    # Application Info
    APP_NAME: str = "IP-Creator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-to-a-secure-key"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/ip_creator.db"
    
    # Redis Configuration (for Celery task queue)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # File Upload Settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB per file
    MAX_UPLOAD_FILES: int = 50  # Maximum files per upload request
    ALLOWED_IMAGE_TYPES: set = Field(default_factory=lambda: {'.jpg', '.jpeg', '.png', '.webp'})
    ALLOWED_MIME_TYPES: set = Field(default_factory=lambda: {'image/jpeg', 'image/png', 'image/webp'})
    MIN_IMAGE_DIMENSION: int = 256  # Minimum width/height in pixels
    MAX_IMAGE_DIMENSION: int = 4096  # Maximum width/height in pixels
    
    # File Storage Paths
    STORAGE_PATH: str = "./data"
    IP_ASSETS_PATH: str = "./data/ip_assets"
    LORA_MODELS_PATH: str = "./data/lora_models"
    VIDEOS_PATH: str = "./data/videos"
    MODELS_PATH: str = "./data/models"
    
    # Encryption
    ENCRYPTION_KEY: str = "change-this-encryption-key"
    
    # Hugging Face Endpoint (for China mirror, e.g. https://hf-mirror.com)
    HF_ENDPOINT: Optional[str] = None
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "change-this-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Default LLM Parameters
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 2048
    DEFAULT_TIMEOUT: int = 60
    
    # GPU & Resource Settings
    GPU_MEMORY_LIMIT: int = 6  # GB
    MAX_CONCURRENT_TASKS: int = 2
    
    # LoRA Training Mode
    # "mock" - Simulated training for workflow validation (fast, no GPU needed)
    # "real" - Real Kohya training (requires GPU, produces actual models)
    LORA_TRAINING_MODE: str = "mock"
    
    # Dataset Quality Assessment Settings
    DATASET_QUALITY_THRESHOLD: float = 30.0  # Default quality score threshold
    DATASET_MIN_IMAGES: int = 15  # Minimum recommended images
    DATASET_MAX_IMAGES: int = 30  # Maximum recommended images
    DATASET_QUALITY_WEIGHTS: dict = Field(default_factory=lambda: {
        "brightness": 0.25,
        "contrast": 0.25,
        "sharpness": 0.25,
        "colorfulness": 0.25
    })
    
    class Config:
        """Pydantic configuration for environment variable loading."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def ensure_directories(self):
        """Create storage directories if they don't exist."""
        directories = [
            self.STORAGE_PATH,
            self.IP_ASSETS_PATH,
            self.LORA_MODELS_PATH,
            self.VIDEOS_PATH,
            self.MODELS_PATH,
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def validate_security_keys(self) -> list[str]:
        """
        Validate that security-sensitive keys are not using default values.
        
        Returns:
            List of warning messages for insecure configurations.
        """
        warnings = []
        
        # Check SECRET_KEY
        if self.SECRET_KEY in [
            "change-this-to-a-secure-key",
            "your-secret-key-change-in-production",
            "secret",
            "key",
        ]:
            warnings.append(
                "SECURITY WARNING: SECRET_KEY is using default value. "
                "Please set a strong random key in production!"
            )
        
        # Check ENCRYPTION_KEY
        if self.ENCRYPTION_KEY in [
            "change-this-encryption-key",
            "your-encryption-key-change-in-production",
        ]:
            warnings.append(
                "SECURITY WARNING: ENCRYPTION_KEY is using default value. "
                "API keys will be encrypted with weak key!"
            )
        
        # Check JWT_SECRET_KEY
        if self.JWT_SECRET_KEY in [
            "change-this-jwt-secret",
            "your-jwt-secret-key",
            "jwt-secret",
        ]:
            warnings.append(
                "SECURITY WARNING: JWT_SECRET_KEY is using default value. "
                "Authentication tokens can be forged!"
            )
        
        return warnings


# Global settings instance
settings = Settings()
