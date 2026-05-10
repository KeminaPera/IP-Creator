"""
Generated Content Model

Stores all generated content (stories, images, videos) with metadata
for browsing, filtering, and management in the Content Library.
"""
from sqlalchemy import Column, Integer, String, Float, Text, JSON, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class GeneratedContent(Base):
    """
    Generated content management.
    
    Stores all AI-generated content including stories, images, and videos
    with rich metadata for browsing, filtering, and IP asset association.
    """
    __tablename__ = "generated_contents"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Task Association
    task_id = Column(String(100), nullable=True, unique=True, index=True, comment="Associated Celery task ID")
    task_type = Column(String(50), nullable=False, index=True, comment="story_generation, image_generation, video_generation")
    
    # Content Type & Metadata
    content_type = Column(String(20), nullable=False, index=True, comment="story, image, video")
    title = Column(String(200), nullable=True, comment="User-friendly content title")
    description = Column(Text, nullable=True, comment="Content description or summary")
    
    # File Storage
    file_path = Column(String(500), nullable=True, comment="Path to generated file")
    thumbnail_path = Column(String(500), nullable=True, comment="Path to thumbnail/preview image")
    file_size = Column(Integer, nullable=True, comment="File size in bytes")
    
    # Media-specific Metadata
    duration_seconds = Column(Integer, nullable=True, comment="Duration for video/audio (seconds)")
    resolution = Column(String(20), nullable=True, comment="Image/video resolution (e.g., 1920x1080)")
    word_count = Column(Integer, nullable=True, comment="Word count for stories")
    
    # IP Asset Association
    ip_asset_id = Column(Integer, ForeignKey("ip_assets.id"), nullable=True, index=True, comment="Associated IP asset ID")
    
    # Content Parameters (input params used for generation)
    parameters = Column(JSON, nullable=True, comment="Generation input parameters")
    
    # Content Metadata (output metadata from generation)
    content_metadata = Column(JSON, nullable=True, comment="Generation output metadata")
    
    # Tagging & Organization
    tags = Column(JSON, nullable=True, comment="Content tags for filtering")
    is_favorite = Column(Boolean, default=False, index=True, comment="User bookmark/favorite flag")
    
    # Status
    status = Column(String(20), default="completed", index=True, comment="completed, failed, deleted")
    error_message = Column(Text, nullable=True, comment="Error details if generation failed")
    
    # Performance Metrics
    execution_time_seconds = Column(Float, nullable=True, comment="Generation time in seconds")
    channel_id = Column(Integer, nullable=True, index=True, comment="LLM channel ID used for generation")
    
    # Metadata
    created_by = Column(Integer, nullable=True, comment="User ID who created the content")
    created_at = Column(DateTime, server_default=func.now(), index=True, comment="Creation timestamp")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), index=True, comment="Update timestamp")
    
    # Relationships
    ip_asset = relationship("IPAsset", backref="generated_contents")
    
    # Composite Indexes for common query patterns
    __table_args__ = (
        # Content library list query: filter by status, type, order by time
        Index('idx_content_status_type_created', 'status', 'content_type', 'created_at'),
        # IP asset content query: filter by IP, status, order by time
        Index('idx_content_ip_status_created', 'ip_asset_id', 'status', 'created_at'),
        # Favorite content query: filter by favorite, order by time
        Index('idx_content_favorite_created', 'is_favorite', 'created_at'),
        # Task content query: filter by task type, status, order by time
        Index('idx_content_task_type_status', 'task_type', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f"<GeneratedContent(id={self.id}, type={self.content_type}, title={self.title})>"
