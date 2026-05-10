"""
LLM Provider and Model Database Models

Stores LLM provider configurations and their available models,
replacing the hardcoded provider registry with database-driven approach.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text, JSON, 
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class LLMProvider(Base):
    """
    LLM Provider configuration.
    
    Stores information about LLM providers (OpenAI, Anthropic, Google, etc.)
    including their branding, API endpoints, and settings.
    """
    __tablename__ = "llm_providers"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Basic Information
    code = Column(String(50), unique=True, nullable=False, index=True, 
                  comment="Unique identifier (e.g., openai, zhipu, ollama)")
    name_cn = Column(String(100), nullable=False, comment="Chinese name")
    name_en = Column(String(100), nullable=False, comment="English name")
    
    # Icon and Branding
    icon_class = Column(String(100), nullable=True, 
                        comment="Font Awesome icon class (e.g., fa-brands fa-openai)")
    icon_url = Column(String(500), nullable=True, 
                      comment="Icon image path (e.g., /static/images/providers/openai.svg)")
    website = Column(String(500), nullable=True, comment="Official website")
    api_docs_url = Column(String(500), nullable=True, comment="API documentation URL")
    
    # API Configuration
    default_endpoint = Column(String(500), nullable=True, comment="Default API endpoint")
    requires_api_key = Column(Boolean, default=True, comment="Whether API key is required")
    api_key_pattern = Column(String(200), nullable=True, 
                             comment="API key format regex for validation")
    
    # Status and Sorting
    is_active = Column(Boolean, default=True, comment="Whether provider is available")
    is_recommended = Column(Boolean, default=False, comment="Whether provider is recommended")
    sort_order = Column(Integer, default=0, comment="Display order in dropdowns")
    
    # Metadata
    description_cn = Column(Text, nullable=True, comment="Chinese description")
    description_en = Column(Text, nullable=True, comment="English description")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), 
                        comment="Creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), 
                        onupdate=func.now(), comment="Update timestamp")
    last_synced_at = Column(DateTime(timezone=True), nullable=True, 
                          comment="Last successful sync timestamp")
    
    # Relationships
    models = relationship("LLMModel", back_populates="provider", 
                          cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_llm_providers_code', 'code'),
        Index('idx_llm_providers_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<LLMProvider(id={self.id}, code={self.code}, name={self.name_en})>"


class LLMModel(Base):
    """
    LLM Model version information.
    
    Stores individual models available from each provider,
    including capabilities, specifications, and pricing.
    """
    __tablename__ = "llm_models"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Foreign Key Relationship
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=False,
                         comment="Associated provider ID")
    
    # Basic Information
    code = Column(String(100), nullable=False, 
                  comment="Model unique identifier (e.g., gpt-4o, glm-4)")
    name = Column(String(100), nullable=False, comment="Model display name")
    version = Column(String(50), nullable=True, comment="Version number (e.g., 2.0, 3.5)")
    
    # Capability Tags (JSON array)
    capabilities = Column(JSON, nullable=True, 
                          comment='["text_generation", "vision", "code", "chat"]')
    
    # Model Specifications
    max_tokens = Column(Integer, nullable=True, comment="Maximum context length")
    max_output_tokens = Column(Integer, nullable=True, comment="Maximum output length")
    supports_streaming = Column(Boolean, default=True, comment="Supports streaming output")
    supports_function_calling = Column(Boolean, default=False, 
                                       comment="Supports function calling")
    supports_vision = Column(Boolean, default=False, comment="Supports vision/image input")
    
    # Performance Metrics
    input_price_per_million = Column(Float, nullable=True, 
                                      comment="Input price per million tokens")
    output_price_per_million = Column(Float, nullable=True, 
                                       comment="Output price per million tokens")
    speed_rating = Column(Integer, nullable=True, comment="Speed rating 1-5")
    quality_rating = Column(Integer, nullable=True, comment="Quality rating 1-5")
    
    # Status and Sorting
    is_active = Column(Boolean, default=True, comment="Whether model is available")
    is_recommended = Column(Boolean, default=False, comment="Whether model is recommended")
    sort_order = Column(Integer, default=0, comment="Display order in dropdowns")
    
    # Time Information
    release_date = Column(Date, nullable=True, comment="Release date")
    deprecated_date = Column(Date, nullable=True, comment="Deprecation date")
    
    # Metadata
    description = Column(Text, nullable=True, comment="Model description")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), 
                        comment="Creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), 
                        onupdate=func.now(), comment="Update timestamp")
    
    # Relationships
    provider = relationship("LLMProvider", back_populates="models")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('provider_id', 'code', name='uq_provider_model'),
        Index('idx_llm_models_provider', 'provider_id'),
        Index('idx_llm_models_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<LLMModel(id={self.id}, code={self.code}, name={self.name})>"
