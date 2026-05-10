"""
LLM Configuration Model

Stores configuration for both local and cloud LLM models,
including encrypted API keys and health status.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.config.database import Base


class LLMConfig(Base):
    """
    LLM model configuration and health tracking.
    
    Supports both local models (Ollama, local deployments) and 
    cloud models (OpenAI-compatible APIs) with encrypted credentials.
    """
    __tablename__ = "llm_configs"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Model Identification
    name = Column(String(100), nullable=False, index=True, comment="Display name for the model")
    model_type = Column(String(20), nullable=False, index=True, comment="local or cloud")
    provider = Column(String(50), nullable=False, index=True, comment="ollama, openai, zhipu, qwen, etc.")
    model_name = Column(String(100), nullable=False, comment="Actual model identifier")
    
    # Connection Configuration
    api_endpoint = Column(String(500), nullable=True, comment="API endpoint URL for cloud models")
    api_key_encrypted = Column(Text, nullable=True, comment="Encrypted API key for cloud models")
    local_path = Column(String(500), nullable=True, comment="Local model path for local models")
    
    # Model Parameters
    temperature = Column(Float, default=0.7, comment="Sampling temperature")
    max_tokens = Column(Integer, default=2048, comment="Maximum tokens to generate")
    timeout = Column(Integer, default=60, comment="Request timeout in seconds")
    context_window = Column(Integer, default=4096, comment="Context window size")
    additional_params = Column(JSON, nullable=True, comment="Additional model-specific parameters")
    
    # Status & Health
    is_active = Column(Boolean, default=True, index=True, comment="Whether model is available for use")
    is_default = Column(Boolean, default=False, index=True, comment="Default model for the system")
    health_status = Column(String(20), default="unknown", index=True, comment="healthy, unhealthy, unknown")
    last_health_check = Column(DateTime, nullable=True, comment="Last health check time")
    response_time_ms = Column(Float, nullable=True, comment="Exponential moving average response time (ms), alpha=0.2")
    success_rate = Column(Float, default=100.0, comment="Success rate percentage")
    
    # Metadata
    description = Column(Text, nullable=True, comment="Model description")
    created_at = Column(DateTime, server_default=func.now(), comment="Creation timestamp")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="Update timestamp")
    
    # Unique Constraint: Prevent duplicate channels for same provider + model
    __table_args__ = (
        UniqueConstraint('provider', 'model_name', name='uq_provider_model_name'),
        # Active models by type and provider
        Index('idx_llm_type_provider_active', 'model_type', 'provider', 'is_active'),
        # Health monitoring: filter by health status, order by update time
        Index('idx_llm_health_updated', 'health_status', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<LLMConfig(id={self.id}, name={self.name}, type={self.model_type})>"
