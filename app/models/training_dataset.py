"""
Training Dataset Model

Manages training datasets for LoRA model training, including
dataset statistics, quality metrics, and version control.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class TrainingDataset(Base):
    """
    Training dataset management for LoRA fine-tuning.
    
    Tracks datasets used for training LoRA models, including
    quality metrics, validation reports, and version control.
    """
    __tablename__ = "training_datasets"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # IP Asset Association
    ip_asset_id = Column(Integer, ForeignKey("ip_assets.id"), nullable=False, index=True, comment="Which IP this dataset is for")
    
    # Dataset Identification
    name = Column(String(100), nullable=False, comment="Dataset name")
    description = Column(Text, nullable=True, comment="Dataset description")
    
    # Dataset Statistics
    image_count = Column(Integer, default=0, comment="Number of original images")
    augmented_count = Column(Integer, default=0, comment="Number of images after augmentation")
    total_size_mb = Column(Float, default=0.0, comment="Total dataset size in MB")
    
    # Quality Metrics
    quality_score = Column(Float, nullable=True, comment="Overall quality score (0-100)")
    angle_coverage = Column(JSON, nullable=True, comment="Coverage by angle: {\"front\": 10, \"side\": 8, \"back\": 5}")
    diversity_score = Column(Float, nullable=True, comment="Diversity score (0-100)")
    consistency_score = Column(Float, nullable=True, comment="Consistency score (0-100)")
    
    # Status
    status = Column(String(20), default="pending", index=True, comment="pending, validating, ready, training, archived")
    validation_report = Column(JSON, nullable=True, comment="Detailed validation results")
    
    # Version Management
    version = Column(Integer, default=1, comment="Version number")
    parent_version_id = Column(Integer, ForeignKey("training_datasets.id"), nullable=True, comment="Parent version for tracking changes")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="Creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Update timestamp")
    
    # Relationships
    ip_asset = relationship("IPAsset", backref="training_datasets")
    images = relationship("DatasetImage", back_populates="dataset", cascade="all, delete-orphan")
    parent_version = relationship("TrainingDataset", remote_side=[id], backref="child_versions")
    lora_models = relationship("LoRAModel", back_populates="dataset")
    
    # Composite Indexes
    __table_args__ = (
        # Dataset list by IP: filter by ip_asset_id, order by version
        Index('idx_datasets_ip_version', 'ip_asset_id', 'version'),
        # Quality-based queries: filter by status, order by quality
        Index('idx_datasets_status_quality', 'status', 'quality_score'),
    )
    
    def __repr__(self):
        return f"<TrainingDataset(id={self.id}, name={self.name}, status={self.status}, quality={self.quality_score})>"
