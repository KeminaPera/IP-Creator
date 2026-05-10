"""
LoRA Model Asset Model

Tracks trained LoRA models for IP character fine-tuning,
including training parameters and performance metrics.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON, DateTime, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class LoRAModel(Base):
    """
    LoRA fine-tuned model storage and tracking.
    
    Manages trained LoRA models (.safetensors format) with training
    metadata, performance metrics, and IP associations.
    """
    __tablename__ = "lora_models"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Model Identification
    name = Column(String(100), nullable=False, index=True, comment="LoRA model name")
    file_path = Column(String(500), nullable=False, comment="Path to .safetensors file")
    base_model = Column(String(100), nullable=False, index=True, comment="Base model used for training")
    
    # Training Configuration
    training_params = Column(JSON, nullable=True, comment="Training parameters used")
    # Format: {"epochs": 10, "learning_rate": 1e-4, "batch_size": 4, ...}
    
    # Performance Metrics
    final_loss = Column(Float, nullable=True, comment="Final training loss")
    training_steps = Column(Integer, nullable=True, comment="Total training steps")
    training_time_minutes = Column(Float, nullable=True, comment="Total training time")
    
    # Status
    status = Column(String(20), default="training", index=True, comment="training, completed, failed, archived")
    error_message = Column(Text, nullable=True, comment="Error details if training failed")
    
    # Training Progress (for real-time tracking)
    progress = Column(Float, default=0.0, comment="Training progress percentage (0-100)")
    current_loss = Column(Float, nullable=True, comment="Current training loss")
    current_epoch = Column(Integer, default=0, comment="Current training epoch")
    total_epochs = Column(Integer, default=10, comment="Total training epochs")
    started_at = Column(DateTime, nullable=True, comment="Training start time")
    completed_at = Column(DateTime, nullable=True, comment="Training completion time")
    
    # Usage
    weight_default = Column(Float, default=0.7, comment="Default inference weight (0.0-1.0)")
    is_active = Column(Boolean, default=True, index=True, comment="Whether model is available for use")
    
    # Metadata
    description = Column(Text, nullable=True, comment="Model description")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="Creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Update timestamp")
    
    # Relationship
    ip_assets = relationship("IPAsset", back_populates="lora_model")
    
    # Composite Indexes
    __table_args__ = (
        # Model list: filter by status, active, order by creation time
        Index('idx_lora_status_active_created', 'status', 'is_active', 'created_at'),
        # Base model query: filter by base_model, status
        Index('idx_lora_base_status', 'base_model', 'status'),
    )
    
    def __repr__(self):
        return f"<LoRAModel(id={self.id}, name={self.name}, status={self.status})>"
