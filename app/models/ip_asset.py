"""
IP Asset Model

Manages cartoon IP character assets including images, tags,
and LoRA model associations for consistent character generation.
"""
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class IPAsset(Base):
    """
    IP character asset management.
    
    Stores multi-angle reference images, style tags, trigger words,
    and associations with trained LoRA models for consistent generation.
    """
    __tablename__ = "ip_assets"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # IP Identification
    name = Column(String(100), nullable=False, index=True, comment="IP character name")
    category = Column(String(50), nullable=True, index=True, comment="Category: pet, human, fantasy, etc.")
    description = Column(Text, nullable=True, comment="IP character description")
    
    # Image Storage
    reference_images = Column(JSON, nullable=False, comment="List of image paths with angles")
    # Format: [{"angle": "front", "path": "/path/to/image.jpg"}, ...]
    
    # Tag Management
    positive_tags = Column(JSON, nullable=True, comment="Positive style tags")
    negative_tags = Column(JSON, nullable=True, comment="Negative tags to avoid")
    trigger_word = Column(String(100), nullable=False, index=True, comment="Unique trigger word for this IP")
    
    # Style Template
    style_template = Column(String(50), nullable=True, comment="Preset style: 3d_cartoon, blind_box, healing, etc.")
    
    # LoRA Association
    lora_model_id = Column(Integer, ForeignKey("lora_models.id"), nullable=True, index=True, comment="Associated LoRA model ID")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True, comment="Update timestamp")
    
    # Relationship
    lora_model = relationship("LoRAModel", back_populates="ip_assets")
    
    # Composite Indexes
    __table_args__ = (
        # IP list by category: filter by category, order by update time
        Index('idx_ip_category_updated', 'category', 'updated_at'),
        # Trained LoRA IPs: filter by lora_model_id, order by update time
        Index('idx_ip_lora_updated', 'lora_model_id', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<IPAsset(id={self.id}, name={self.name}, trigger={self.trigger_word})>"
