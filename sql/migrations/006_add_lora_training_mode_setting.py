#!/usr/bin/env python3
"""
Add LoRA Training Mode Setting

Adds the lora_training_mode configuration to system_settings table.
"""
import asyncio
from sqlalchemy import text
from app.config.database import async_session_factory
from app.utils.logger import logger


async def add_lora_training_mode_setting():
    """Add lora_training_mode setting to database."""
    
    setting_sql = """
    INSERT INTO system_settings (
        category, setting_key, setting_value, value_type,
        display_name_cn, display_name_en,
        description_cn, description_en,
        validation_rule, default_value,
        is_system, is_active
    )
    VALUES (
        'system_feature', 'lora_training_mode', 'mock', 'string',
        'LoRA训练模式', 'LoRA Training Mode',
        '训练模式：mock（模拟训练，用于流程验证）或real（真实Kohya训练）',
        'Training mode: mock (simulated for workflow validation) or real (real Kohya training)',
        '{"options": ["mock", "real"]}', 'mock',
        0, 1
    )
    ON CONFLICT (category, setting_key) DO NOTHING
    """
    
    async with async_session_factory() as db:
        try:
            # Check if setting already exists
            result = await db.execute(
                text("SELECT COUNT(*) FROM system_settings WHERE category='system_feature' AND setting_key='lora_training_mode'")
            )
            count = result.scalar()
            
            if count > 0:
                logger.info("lora_training_mode setting already exists")
                return
            
            # Add the setting
            await db.execute(text(setting_sql))
            await db.commit()
            
            logger.info("Successfully added lora_training_mode setting")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to add lora_training_mode setting: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(add_lora_training_mode_setting())
