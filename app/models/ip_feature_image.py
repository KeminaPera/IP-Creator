"""
IP Feature Image Model

Manages images for each feature in the IP feature library.
Each feature can have multiple images from different angles (front/side/back).
"""
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class IPFeatureImage(Base):
    """
    IP feature image management.
    
    Stores images for each feature (outfit, expression, pose, etc.) from different angles.
    These images are used for LoRA training dataset generation.
    """
    __tablename__ = "ip_feature_images"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Feature Association
    feature_id = Column(Integer, ForeignKey("ip_feature_library.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Angle
    angle = Column(String(20), nullable=False, index=True, comment="View angle: front, side, back")
    
    # Image Path
    image_path = Column(String(500), nullable=False, comment="Path to the image file")
    width = Column(Integer, comment="Image width in pixels")
    height = Column(Integer, comment="Image height in pixels")
    
    # Source
    source = Column(String(20), nullable=False, comment="Source: generated (AI) or uploaded (user)")
    
    # Generation Parameters
    generation_params = Column(JSON, comment="Generation parameters if AI generated")
    
    # Quality
    quality_score = Column(Float, comment="Quality score 0-100")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp")
    
    # Relationship
    feature = relationship("IPFeatureLibrary", back_populates="images")
    
    # Indexes
    __table_args__ = (
        Index('idx_feature_images_feature_angle', 'feature_id', 'angle'),
    )
    
    def __repr__(self):
        return f"<IPFeatureImage(id={self.id}, feature_id={self.feature_id}, angle={self.angle})>"
