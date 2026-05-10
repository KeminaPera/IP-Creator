"""
Dataset Image Model

Manages individual images within training datasets, including
annotations, quality scores, and augmentation tracking.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class DatasetImage(Base):
    """
    Individual images within training datasets.
    
    Tracks image metadata, annotations, quality scores, and
    augmentation relationships for LoRA training datasets.
    """
    __tablename__ = "dataset_images"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Dataset Association
    dataset_id = Column(Integer, ForeignKey("training_datasets.id", ondelete="CASCADE"), nullable=False, index=True, comment="Parent dataset")
    
    # File Information
    file_path = Column(String(500), nullable=False, comment="Path to the image file")
    width = Column(Integer, nullable=True, comment="Image width in pixels")
    height = Column(Integer, nullable=True, comment="Image height in pixels")
    file_size_kb = Column(Integer, nullable=True, comment="File size in KB")
    
    # Annotations
    angle = Column(String(20), nullable=True, comment="front, side, back, full_body, half_body")
    expression = Column(String(50), nullable=True, comment="happy, sad, angry, surprised, neutral")
    pose = Column(String(50), nullable=True, comment="standing, sitting, running, jumping")
    background = Column(String(50), nullable=True, comment="simple, complex, outdoor, indoor")
    
    # Quality Assessment
    quality_score = Column(Float, nullable=True, comment="Image quality score (0-100)")
    
    # Augmentation Tracking
    is_augmented = Column(Boolean, default=False, comment="Whether this is an augmented image")
    parent_image_id = Column(Integer, ForeignKey("dataset_images.id"), nullable=True, comment="Original image if augmented")
    
    # Usage Status
    is_selected = Column(Boolean, default=True, comment="Whether selected for training")
    rejection_reason = Column(String(200), nullable=True, comment="Reason for rejection if not selected")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Upload timestamp")
    
    # Relationships
    dataset = relationship("TrainingDataset", back_populates="images")
    parent_image = relationship("DatasetImage", remote_side=[id], backref="augmented_versions")
    
    # Composite Indexes
    __table_args__ = (
        # Images by dataset: filter by dataset_id, order by quality
        Index('idx_images_dataset_quality', 'dataset_id', 'quality_score'),
        # Selection queries: filter by is_selected, is_augmented
        Index('idx_images_selected_augmented', 'is_selected', 'is_augmented'),
        # Angle-based queries: filter by angle, is_selected
        Index('idx_images_angle_selected', 'angle', 'is_selected'),
    )
    
    def __repr__(self):
        return f"<DatasetImage(id={self.id}, angle={self.angle}, quality={self.quality_score})>"
