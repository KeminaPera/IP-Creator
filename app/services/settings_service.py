"""
System Settings Service

Manages system-wide configuration settings with Redis caching support
for optimal performance.
"""
import json
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system_setting import SystemSetting
from app.utils.logger import logger


class SystemSettingsService:
    """Service for managing system settings from database"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def get_settings_by_category(
        self, 
        db: AsyncSession, 
        category: str
    ) -> Dict[str, Any]:
        """
        Get all settings in a category
        
        Args:
            db: Database session
            category: Setting category (llm_default, resource_limit, etc.)
            
        Returns:
            Dict of setting_key: value pairs
        """
        # Check cache first
        if category in self._cache:
            logger.debug(f"Returning cached settings for category: {category}")
            return self._cache[category].copy()
        
        # Query database
        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.category == category,
                SystemSetting.is_active == True
            )
        )
        settings = result.scalars().all()
        
        # Convert to dict with type conversion
        settings_dict = {}
        for setting in settings:
            settings_dict[setting.setting_key] = self._convert_value(
                setting.setting_value,
                setting.value_type
            )
        
        # Cache the result
        self._cache[category] = settings_dict
        logger.info(f"Loaded and cached {len(settings_dict)} settings for category: {category}")
        
        return settings_dict
    
    async def get_all_settings(self, db: AsyncSession) -> Dict[str, Dict[str, Any]]:
        """
        Get all settings grouped by category
        
        Args:
            db: Database session
            
        Returns:
            Dict of category: {key: value} pairs
        """
        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.is_active == True
            )
        )
        settings = result.scalars().all()
        
        # Group by category
        settings_by_category: Dict[str, Dict[str, Any]] = {}
        for setting in settings:
            if setting.category not in settings_by_category:
                settings_by_category[setting.category] = {}
            
            settings_by_category[setting.category][setting.setting_key] = self._convert_value(
                setting.setting_value,
                setting.value_type
            )
        
        # Update cache
        self._cache = settings_by_category
        
        return settings_by_category
    
    async def update_setting(
        self,
        db: AsyncSession,
        category: str,
        key: str,
        value: Any,
        user_id: int = None
    ) -> bool:
        """
        Update a single setting
        
        Args:
            db: Database session
            category: Setting category
            key: Setting key
            value: New value
            user_id: User ID who made the change
            
        Returns:
            True if successful
        """
        # Get existing setting
        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.category == category,
                SystemSetting.setting_key == key
            )
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            raise ValueError(f"Setting not found: {category}.{key}")
        
        # Validate value
        self._validate_value(value, setting.validation_rule, setting.value_type)
        
        # Update
        setting.setting_value = str(value)
        setting.updated_by = user_id
        
        await db.commit()
        
        # Invalidate cache for this category
        if category in self._cache:
            del self._cache[category]
        
        logger.info(f"Setting updated: {category}.{key} = {value} by user {user_id}")
        
        return True
    
    async def reset_to_default(
        self,
        db: AsyncSession,
        category: str,
        user_id: int = None
    ) -> int:
        """
        Reset all settings in a category to their default values
        
        Args:
            db: Database session
            category: Setting category
            user_id: User ID who made the change
            
        Returns:
            Number of settings reset
        """
        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.category == category,
                SystemSetting.is_active == True,
                SystemSetting.default_value.isnot(None)
            )
        )
        settings = result.scalars().all()
        
        count = 0
        for setting in settings:
            setting.setting_value = setting.default_value
            setting.updated_by = user_id
            count += 1
        
        await db.commit()
        
        # Invalidate cache
        if category in self._cache:
            del self._cache[category]
        
        logger.info(f"Reset {count} settings to default for category: {category}")
        
        return count
    
    async def get_setting_detail(
        self,
        db: AsyncSession,
        category: str,
        key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a single setting
        
        Args:
            db: Database session
            category: Setting category
            key: Setting key
            
        Returns:
            Dict with setting details or None
        """
        result = await db.execute(
            select(SystemSetting).where(
                SystemSetting.category == category,
                SystemSetting.setting_key == key
            )
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            return None
        
        return {
            'id': setting.id,
            'category': setting.category,
            'setting_key': setting.setting_key,
            'setting_value': self._convert_value(setting.setting_value, setting.value_type),
            'value_type': setting.value_type,
            'display_name_cn': setting.display_name_cn,
            'display_name_en': setting.display_name_en,
            'description_cn': setting.description_cn,
            'description_en': setting.description_en,
            'validation_rule': setting.validation_rule,
            'default_value': self._convert_value(setting.default_value, setting.value_type),
            'is_system': setting.is_system,
            'updated_at': setting.updated_at,
            'updated_by': setting.updated_by
        }
    
    def _convert_value(self, value_str: str, value_type: str) -> Any:
        """
        Convert string value to appropriate type
        
        Args:
            value_str: String representation of value
            value_type: Target type (string, integer, float, boolean, json)
            
        Returns:
            Converted value
        """
        if value_str is None:
            return None
        
        try:
            if value_type == 'integer':
                return int(value_str)
            elif value_type == 'float':
                return float(value_str)
            elif value_type == 'boolean':
                return value_str.lower() in ('true', '1', 'yes')
            elif value_type == 'json':
                return json.loads(value_str)
            else:
                return value_str
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to convert value '{value_str}' to {value_type}: {e}")
            return value_str
    
    def _validate_value(self, value: Any, validation_rule: Optional[Dict], value_type: str):
        """
        Validate value against rules
        
        Args:
            value: Value to validate
            validation_rule: Validation rules dict
            value_type: Value type
            
        Raises:
            ValueError if validation fails
        """
        if not validation_rule:
            return
        
        # Check required
        if validation_rule.get('required') and (value is None or value == ''):
            raise ValueError("Value is required")
        
        # Check min/max for numeric types
        if value_type in ('integer', 'float') and value is not None:
            min_val = validation_rule.get('min')
            max_val = validation_rule.get('max')
            
            if min_val is not None and value < min_val:
                raise ValueError(f"Value must be >= {min_val}")
            
            if max_val is not None and value > max_val:
                raise ValueError(f"Value must be <= {max_val}")
        
        # Check pattern for strings
        if value_type == 'string' and isinstance(value, str):
            import re
            pattern = validation_rule.get('pattern')
            if pattern and not re.match(pattern, value):
                raise ValueError(f"Value does not match pattern: {pattern}")


# Global instance
settings_service = SystemSettingsService()
