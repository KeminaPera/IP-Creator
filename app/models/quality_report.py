"""
Quality Report Model

Stores quality assessment results for trained LoRA models,
including scores, test images, and optimization recommendations.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class QualityReport(Base):
    """
    Quality assessment report for LoRA models.
    
    Stores comprehensive quality metrics, test image results,
    and optimization recommendations.
    """
    __tablename__ = "quality_reports"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # LoRA Model Association
    lora_id = Column(Integer, ForeignKey("lora_models.id"), nullable=False, index=True, comment="Which LoRA model this report is for")
    
    # Overall Assessment
    overall_score = Column(Float, nullable=False, comment="Overall quality score (0-100)")
    grade = Column(String(2), nullable=False, comment="Quality grade: S, A, B, C, D, F")
    
    # Detailed Scores (0-100 each)
    loss_score = Column(Float, nullable=True, comment="Training loss analysis score")
    completion_score = Column(Float, nullable=True, comment="Training completion score")
    file_score = Column(Float, nullable=True, comment="Model file quality score")
    generation_success = Column(Float, nullable=True, comment="Image generation success rate")
    clip_consistency = Column(Float, nullable=True, comment="CLIP character consistency score")
    
    # Test Images
    test_images = Column(JSON, nullable=True, comment="Generated test images info: [{prompt, path, seed, scenario}]")
    
    # Recommendations
    recommendations = Column(JSON, nullable=True, comment="Optimization recommendations: [str]")
    
    # Assessment Metadata
    assessment_method = Column(String(50), default="automated", comment="Assessment method: automated, manual, hybrid")
    status = Column(String(20), default="completed", comment="Report status: pending, processing, completed, failed")
    error_message = Column(Text, nullable=True, comment="Error message if assessment failed")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, comment="Assessment timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Update timestamp")
    
    # Relationships
    lora_model = relationship("LoRAModel", back_populates="quality_reports")
    
    # Indexes
    __table_args__ = (
        Index('idx_quality_reports_lora', 'lora_id'),
        Index('idx_quality_reports_grade', 'grade'),
        Index('idx_quality_reports_score', 'overall_score'),
    )
    
    def __repr__(self):
        return f"<QualityReport(id={self.id}, lora_id={self.lora_id}, score={self.overall_score}, grade={self.grade})>"
