"""
IP Multi-View Model

Manages standard multi-view images (front/side/back) for IP assets.
These views are used for display and basic generation.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class IPMultiView(Base):
    """
    IP multi-view image management.
    
    Stores standard view images (front, side, back) for each IP asset.
    These can be AI-generated or manually uploaded.
    """
    __tablename__ = "ip_multi_views"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # IP Asset Association
    ip_asset_id = Column(Integer, ForeignKey("ip_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # View Type
    view_type = Column(String(20), nullable=False, index=True, comment="View type: front, side, back, three_quarter_front, three_quarter_back")
    
    # Image Information
    image_path = Column(String(500), nullable=False, comment="Path to the image file")
    width = Column(Integer, comment="Image width in pixels")
    height = Column(Integer, comment="Image height in pixels")
    
    # Source
    source = Column(String(20), nullable=False, comment="Source: generated (AI) or uploaded (user)")
    
    # Generation Parameters (if AI generated)
    generation_params = Column(JSON, comment="Generation parameters: prompt, seed, model, etc.")
    
    # Status
    is_primary = Column(Boolean, default=False, index=True, comment="Whether this is the primary view for display")
    quality_score = Column(Float, comment="Quality score 0-100")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp")
    
    # Relationship
    ip_asset = relationship("IPAsset", back_populates="multi_views")
    
    # Indexes
    __table_args__ = (
        Index('idx_multi_views_ip_type', 'ip_asset_id', 'view_type'),
    )
    
    def __repr__(self):
        return f"<IPMultiView(id={self.id}, ip_asset_id={self.ip_asset_id}, view_type={self.view_type})>"
