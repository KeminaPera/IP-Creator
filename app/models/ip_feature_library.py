"""
IP Feature Library Model

Manages character features (outfits, expressions, poses, etc.) for IP assets.
Each feature can have multiple images from different angles.
Supports extensible feature types without schema changes.
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, JSON, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class IPFeatureLibrary(Base):
    """
    IP feature library management.
    
    Stores diverse character features that can be combined for LoRA training.
    Features include outfits, expressions, poses, and other extensible types.
    """
    __tablename__ = "ip_feature_library"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # IP Asset Association
    ip_asset_id = Column(Integer, ForeignKey("ip_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Feature Type (Extensible)
    feature_type = Column(String(50), nullable=False, index=True, comment="Feature type: outfit, expression, pose, background, accessory, etc.")
    
    # Feature Identification
    feature_name = Column(String(100), nullable=False, comment="Feature name in English: casual_wear, kimono, happy, standing")
    
    # Display Name
    display_name = Column(String(100), comment="Display name in user's language: 常服, 和服, 开心, 站立")
    
    # Description
    description = Column(Text, comment="Feature description")
    
    # Trigger Phrase for Generation
    trigger_phrase = Column(String(200), comment="Trigger phrase for generation: wearing casual clothes, happy expression")
    
    # Reference Images (JSON array for quick access)
    reference_images = Column(JSON, comment="Reference images: [{angle: front, path: /path.jpg}, ...]")
    
    # Status
    is_active = Column(Boolean, default=True, index=True, comment="Whether this feature is active")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Update timestamp")
    
    # Relationships
    ip_asset = relationship("IPAsset", back_populates="feature_library")
    images = relationship("IPFeatureImage", back_populates="feature", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_feature_library_ip_type', 'ip_asset_id', 'feature_type'),
        Index('idx_feature_library_name', 'feature_name'),
        # Unique constraint: one feature per IP per type per name
        Index('idx_feature_library_unique', 'ip_asset_id', 'feature_type', 'feature_name', unique=True),
    )
    
    def __repr__(self):
        return f"<IPFeatureLibrary(id={self.id}, ip_asset_id={self.ip_asset_id}, type={self.feature_type}, name={self.feature_name})>"
