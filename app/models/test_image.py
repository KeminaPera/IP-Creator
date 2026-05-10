"""
Test Image Model

Manages generated test images for LoRA model quality assessment,
including generation parameters and quality metrics.
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class TestImage(Base):
    """
    Test images generated for LoRA model quality assessment.
    
    Stores images generated with trained LoRA models along with
    generation parameters and quality assessment scores.
    """
    __tablename__ = "test_images"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # LoRA Model Association
    lora_model_id = Column(Integer, ForeignKey("lora_models.id", ondelete="CASCADE"), nullable=False, index=True, comment="Which LoRA model this test is for")
    
    # File Information
    file_path = Column(String(500), nullable=False, comment="Path to the test image file")
    
    # Generation Parameters
    prompt = Column(Text, nullable=True, comment="Prompt used to generate this test image")
    negative_prompt = Column(Text, nullable=True, comment="Negative prompt used")
    
    # Quality Metrics
    quality_score = Column(Float, nullable=True, comment="Image quality score (0-100)")
    consistency_score = Column(Float, nullable=True, comment="IP consistency score (0-100)")
    
    # Test Category
    test_category = Column(String(50), nullable=True, comment="front_view, side_view, expression, action, etc.")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Generation timestamp")
    
    # Relationships
    lora_model = relationship("LoRAModel", backref="test_images")
    
    # Composite Indexes
    __table_args__ = (
        # Test images by LoRA: filter by lora_model_id, order by consistency
        Index('idx_test_lora_consistency', 'lora_model_id', 'consistency_score'),
        # Category-based queries: filter by test_category
        Index('idx_test_category', 'test_category'),
    )
    
    def __repr__(self):
        return f"<TestImage(id={self.id}, category={self.test_category}, consistency={self.consistency_score})>"
