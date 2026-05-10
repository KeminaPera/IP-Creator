"""
System Settings Model

Stores system-wide configuration settings in a unified table,
replacing hardcoded settings.py values with database-driven approach.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, JSON, 
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.sql import func
from app.config.database import Base


class SystemSetting(Base):
    """
    System settings storage for dynamic configuration management.
    
    Supports multiple categories of settings including LLM defaults,
    resource limits, storage paths, and system features.
    """
    __tablename__ = "system_settings"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Setting Category
    category = Column(String(50), nullable=False, index=True, 
                     comment="Setting category: llm_default, resource_limit, storage_path, system_feature, ui_preference")
    
    # Setting Key-Value
    setting_key = Column(String(100), nullable=False, comment="Setting key name")
    setting_value = Column(Text, nullable=True, comment="Setting value (stored as string)")
    value_type = Column(String(20), default='string', comment="Value type: string, integer, float, boolean, json")
    
    # Display Information
    display_name_cn = Column(String(100), nullable=True, comment="Chinese display name")
    display_name_en = Column(String(100), nullable=True, comment="English display name")
    description_cn = Column(Text, nullable=True, comment="Chinese description")
    description_en = Column(Text, nullable=True, comment="English description")
    
    # Validation Rules
    validation_rule = Column(JSON, nullable=True, 
                            comment='Validation rules: {"min": 0, "max": 100, "required": true}')
    
    # Default Value
    default_value = Column(Text, nullable=True, comment="Default value")
    
    # Status
    is_active = Column(Boolean, default=True, index=True, comment="Whether setting is active")
    is_system = Column(Boolean, default=False, comment="Whether it's a system-level setting (requires caution)")
    
    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Update timestamp")
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="User ID who last updated")
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('category', 'setting_key', name='uq_category_key'),
        Index('idx_settings_category', 'category'),
        Index('idx_settings_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<SystemSetting(category={self.category}, key={self.setting_key}, value={self.setting_value})>"
