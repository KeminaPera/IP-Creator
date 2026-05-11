"""
Training Configuration Schema

Defines validation and serialization for LoRA training configurations,
including parameter validation and preset management.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum


class LearningRateScheduler(str, Enum):
    """Learning rate scheduler types."""
    COSINE = "cosine"
    COSINE_WITH_RESTARTS = "cosine_with_restarts"
    CONSTANT = "constant"
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"


class OptimizerType(str, Enum):
    """Optimizer types."""
    ADAMW = "AdamW"
    ADAMW_8BIT = "AdamW8bit"
    DADAPT_ADAM = "DAdaptAdam"
    DADAPT_LION = "DAdaptLion"
    LION = "Lion"
    SGD = "SGD"


class ResolutionPreset(str, Enum):
    """Resolution presets."""
    SD_1_5 = 512
    SD_XL = 1024
    CUSTOM = "custom"


class TrainingPreset(BaseModel):
    """Training preset configuration."""
    name: str
    display_name: str
    description: str
    config: Dict[str, Any]
    recommended_for: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "quick_train",
                "display_name": "快速训练",
                "description": "适合快速测试的低epochs配置",
                "config": {
                    "epochs": 5,
                    "learning_rate": 1e-4,
                    "batch_size": 1,
                    "network_dim": 32
                },
                "recommended_for": ["testing", "experimentation"]
            }
        }


class LoRATrainingConfig(BaseModel):
    """
    Complete LoRA training configuration.
    
    Validates all training parameters and provides
    sensible defaults for common use cases.
    """
    
    # Base Model
    base_model: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Base model path or identifier"
    )
    
    # Dataset
    dataset_id: int = Field(
        ...,
        gt=0,
        description="Training dataset ID"
    )
    
    # Output Configuration
    output_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Output model name",
        pattern=r"^[a-zA-Z0-9_-]+$"
    )
    
    # Training Parameters
    resolution: int = Field(
        default=512,
        ge=256,
        le=2048,
        description="Image resolution for training"
    )
    
    batch_size: int = Field(
        default=1,
        ge=1,
        le=16,
        description="Training batch size"
    )
    
    epochs: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of training epochs"
    )
    
    max_train_steps: Optional[int] = Field(
        default=None,
        gt=0,
        description="Max training steps (overrides epochs if set)"
    )
    
    # Learning Rate
    learning_rate: float = Field(
        default=1e-4,
        gt=0,
        lt=1.0,
        description="Learning rate"
    )
    
    lr_scheduler: LearningRateScheduler = Field(
        default=LearningRateScheduler.COSINE_WITH_RESTARTS,
        description="Learning rate scheduler"
    )
    
    lr_warmup_steps: int = Field(
        default=0,
        ge=0,
        description="Learning rate warmup steps"
    )
    
    # LoRA Network
    network_dim: int = Field(
        default=64,
        ge=8,
        le=256,
        description="LoRA network dimension (rank)"
    )
    
    network_alpha: int = Field(
        default=32,
        ge=1,
        description="LoRA network alpha"
    )
    
    # Optimizer
    optimizer_type: OptimizerType = Field(
        default=OptimizerType.ADAMW_8BIT,
        description="Optimizer type"
    )
    
    # Advanced
    mixed_precision: str = Field(
        default="fp16",
        pattern=r"^(no|fp16|bf16)$",
        description="Mixed precision mode"
    )
    
    gradient_checkpointing: bool = Field(
        default=False,
        description="Enable gradient checkpointing to save VRAM"
    )
    
    save_every_n_epochs: int = Field(
        default=1,
        ge=1,
        description="Save checkpoint every N epochs"
    )
    
    # Metadata
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Training description"
    )
    
    @validator('network_alpha')
    def validate_alpha(cls, v, values):
        """Alpha should typically be <= network_dim."""
        if 'network_dim' in values and v > values['network_dim']:
            # Warning but allow (some advanced configurations use alpha > dim)
            pass
        return v
    
    @validator('max_train_steps')
    def validate_steps(cls, v, values):
        """Either epochs or max_train_steps should be set."""
        if v is None and values.get('epochs') is None:
            raise ValueError("Either epochs or max_train_steps must be set")
        return v
    
    def to_kohya_config(self) -> Dict[str, Any]:
        """Convert to Kohya-sd configuration format."""
        return {
            "pretrained_model_name_or_path": self.base_model,
            "output_name": self.output_name,
            "resolution": self.resolution,
            "train_batch_size": self.batch_size,
            "max_train_epochs": self.epochs,
            "max_train_steps": self.max_train_steps,
            "learning_rate": self.learning_rate,
            "lr_scheduler": self.lr_scheduler.value,
            "lr_warmup_steps": self.lr_warmup_steps,
            "network_dim": self.network_dim,
            "network_alpha": self.network_alpha,
            "optimizer_type": self.optimizer_type.value,
            "mixed_precision": self.mixed_precision,
            "gradient_checkpointing": self.gradient_checkpointing,
            "save_every_n_epochs": self.save_every_n_epochs,
        }


class TrainingConfigResponse(BaseModel):
    """Response schema for training configuration."""
    success: bool
    config: LoRATrainingConfig
    estimated_time_minutes: Optional[float] = None
    recommendations: List[str] = []


# Preset configurations
TRAINING_PRESETS = {
    "quick_test": TrainingPreset(
        name="quick_test",
        display_name="快速测试",
        description="快速测试训练配置，适合验证流程",
        config={
            "epochs": 3,
            "learning_rate": 1e-4,
            "batch_size": 1,
            "network_dim": 32,
            "network_alpha": 16,
            "resolution": 512,
        },
        recommended_for=["testing", "validation"]
    ),
    
    "standard": TrainingPreset(
        name="standard",
        display_name="标准训练",
        description="标准训练配置，平衡质量和时间",
        config={
            "epochs": 10,
            "learning_rate": 1e-4,
            "batch_size": 1,
            "network_dim": 64,
            "network_alpha": 32,
            "resolution": 512,
        },
        recommended_for=["general", "characters"]
    ),
    
    "high_quality": TrainingPreset(
        name="high_quality",
        display_name="高质量训练",
        description="高质量训练配置，适合最终模型",
        config={
            "epochs": 20,
            "learning_rate": 5e-5,
            "batch_size": 2,
            "network_dim": 128,
            "network_alpha": 64,
            "resolution": 768,
        },
        recommended_for=["production", "high-quality"]
    ),
    
    "anime_style": TrainingPreset(
        name="anime_style",
        display_name="动漫风格",
        description="针对动漫风格优化的配置",
        config={
            "epochs": 15,
            "learning_rate": 1e-4,
            "batch_size": 1,
            "network_dim": 64,
            "network_alpha": 32,
            "resolution": 512,
        },
        recommended_for=["anime", "illustration"]
    ),
}


def get_preset(preset_name: str) -> Optional[TrainingPreset]:
    """Get training preset by name."""
    return TRAINING_PRESETS.get(preset_name)


def list_presets() -> List[TrainingPreset]:
    """List all available training presets."""
    return list(TRAINING_PRESETS.values())


def estimate_training_time(config: LoRATrainingConfig) -> float:
    """
    Estimate training time in minutes.
    
    This is a rough estimate based on configuration.
    Actual time depends on GPU, dataset size, etc.
    """
    # Base time per epoch (minutes)
    base_time = 5.0
    
    # Adjust for resolution
    resolution_factor = (config.resolution / 512) ** 2
    
    # Adjust for batch size
    batch_factor = 1.0 / config.batch_size
    
    # Adjust for network dimension
    dim_factor = config.network_dim / 64.0
    
    # Calculate estimate
    total_time = base_time * config.epochs * resolution_factor * batch_factor * dim_factor
    
    return round(total_time, 1)


class StartTrainingRequest(BaseModel):
    """Request schema for starting LoRA training."""
    
    use_preset: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Training preset name (e.g., 'quick_test', 'standard')"
    )
    
    custom_config: Optional[LoRATrainingConfig] = Field(
        default=None,
        description="Custom training configuration (overrides preset)"
    )
    
    @validator("use_preset")
    def validate_preset(cls, v):
        """Validate preset exists."""
        if v is not None:
            preset = get_preset(v)
            if not preset:
                raise ValueError(f"Unknown preset: {v}. Available: {', '.join(TRAINING_PRESETS.keys())}")
        return v
