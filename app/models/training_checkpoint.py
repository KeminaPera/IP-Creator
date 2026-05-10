"""
Training Checkpoint Model

Manages training checkpoint files during LoRA training,
including training progress and recommendation status.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class TrainingCheckpoint(Base):
    """
    Training checkpoints saved during LoRA fine-tuning.
    
    Tracks checkpoint files, training progress metrics, and
    recommendations for which checkpoint to use.
    """
    __tablename__ = "training_checkpoints"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # LoRA Model Association
    lora_model_id = Column(Integer, ForeignKey("lora_models.id", ondelete="CASCADE"), nullable=False, index=True, comment="Parent LoRA model")
    
    # Checkpoint File
    file_path = Column(String(500), nullable=False, comment="Path to the checkpoint .safetensors file")
    
    # Training Progress
    epoch = Column(Integer, nullable=False, comment="Epoch number when this checkpoint was saved")
    step = Column(Integer, nullable=True, comment="Step number within the epoch")
    loss = Column(Float, nullable=True, comment="Training loss value at this point")
    
    # Recommendation
    is_recommended = Column(Boolean, default=False, comment="Whether this checkpoint is recommended as the best")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Checkpoint save timestamp")
    
    # Relationships
    lora_model = relationship("LoRAModel", backref="checkpoints")
    
    # Composite Indexes
    __table_args__ = (
        # Checkpoints by LoRA: filter by lora_model_id, order by epoch
        Index('idx_checkpoints_lora_epoch', 'lora_model_id', 'epoch'),
        # Recommended checkpoint: filter by is_recommended
        Index('idx_checkpoints_recommended', 'is_recommended'),
    )
    
    def __repr__(self):
        return f"<TrainingCheckpoint(id={self.id}, epoch={self.epoch}, loss={self.loss})>"
