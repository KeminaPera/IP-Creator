#!/usr/bin/env python3
"""
Initialize System Settings

Populates the system_settings table with default configuration values
for all setting categories.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import async_session_factory
from app.models.system_setting import SystemSetting
from app.utils.logger import logger


async def init_system_settings():
    """Initialize all system settings with default values."""
    
    settings_data = [
        # LLM Default Parameters
        {
            "category": "llm_default",
            "setting_key": "temperature",
            "setting_value": "0.7",
            "value_type": "float",
            "display_name_cn": "温度参数",
            "display_name_en": "Temperature",
            "description_cn": "控制AI输出的随机性，值越高越创意，值越低越保守",
            "description_en": "Controls randomness of AI output. Higher values are more creative, lower values more conservative",
            "validation_rule": '{"min": 0.0, "max": 2.0}',
            "default_value": "0.7",
            "is_system": False,
            "is_active": True
        },
        {
            "category": "llm_default",
            "setting_key": "max_tokens",
            "setting_value": "2048",
            "value_type": "integer",
            "display_name_cn": "最大Token数",
            "display_name_en": "Max Tokens",
            "description_cn": "单次AI生成的最大token数量",
            "description_en": "Maximum number of tokens for single AI generation",
            "validation_rule": '{"min": 1, "max": 8192}',
            "default_value": "2048",
            "is_system": False,
            "is_active": True
        },
        {
            "category": "llm_default",
            "setting_key": "timeout",
            "setting_value": "60",
            "value_type": "integer",
            "display_name_cn": "超时时间",
            "display_name_en": "Timeout",
            "description_cn": "API请求超时时间（秒）",
            "description_en": "API request timeout in seconds",
            "validation_rule": '{"min": 10, "max": 300}',
            "default_value": "60",
            "is_system": False,
            "is_active": True
        },
        
        # Resource Limits
        {
            "category": "resource_limit",
            "setting_key": "max_upload_size",
            "setting_value": "50",
            "value_type": "integer",
            "display_name_cn": "最大上传文件大小",
            "display_name_en": "Max Upload Size",
            "description_cn": "允许上传的最大文件大小（MB）",
            "description_en": "Maximum allowed upload file size in MB",
            "validation_rule": '{"min": 1, "max": 500}',
            "default_value": "50",
            "is_system": False,
            "is_active": True
        },
        {
            "category": "resource_limit",
            "setting_key": "max_concurrent_tasks",
            "setting_value": "2",
            "value_type": "integer",
            "display_name_cn": "最大并发任务数",
            "display_name_en": "Max Concurrent Tasks",
            "description_cn": "同时运行的最大任务数量",
            "description_en": "Maximum number of concurrent tasks",
            "validation_rule": '{"min": 1, "max": 10}',
            "default_value": "2",
            "is_system": False,
            "is_active": True
        },
        {
            "category": "resource_limit",
            "setting_key": "gpu_memory_limit",
            "setting_value": "6",
            "value_type": "integer",
            "display_name_cn": "GPU内存限制",
            "display_name_en": "GPU Memory Limit",
            "description_cn": "单个任务的GPU内存使用限制（GB）",
            "description_en": "GPU memory limit per task in GB",
            "validation_rule": '{"min": 2, "max": 24}',
            "default_value": "6",
            "is_system": False,
            "is_active": True
        },
        
        # Storage Paths
        {
            "category": "storage_path",
            "setting_key": "storage_path",
            "setting_value": "./data",
            "value_type": "string",
            "display_name_cn": "主存储路径",
            "display_name_en": "Main Storage Path",
            "description_cn": "所有数据的根存储目录",
            "description_en": "Root storage directory for all data",
            "validation_rule": None,
            "default_value": "./data",
            "is_system": True,
            "is_active": True
        },
        {
            "category": "storage_path",
            "setting_key": "ip_assets_path",
            "setting_value": "./data/ip_assets",
            "value_type": "string",
            "display_name_cn": "IP资产路径",
            "display_name_en": "IP Assets Path",
            "description_cn": "存储IP资产参考图片的目录",
            "description_en": "Directory for IP asset reference images",
            "validation_rule": None,
            "default_value": "./data/ip_assets",
            "is_system": True,
            "is_active": True
        },
        {
            "category": "storage_path",
            "setting_key": "lora_models_path",
            "setting_value": "./data/lora_models",
            "value_type": "string",
            "display_name_cn": "LoRA模型路径",
            "display_name_en": "LoRA Models Path",
            "description_cn": "存储训练完成的LoRA模型的目录",
            "description_en": "Directory for trained LoRA models",
            "validation_rule": None,
            "default_value": "./data/lora_models",
            "is_system": True,
            "is_active": True
        },
        {
            "category": "storage_path",
            "setting_key": "videos_path",
            "setting_value": "./data/videos",
            "value_type": "string",
            "display_name_cn": "视频输出路径",
            "display_name_en": "Videos Output Path",
            "description_cn": "存储生成视频的目录",
            "description_en": "Directory for generated videos",
            "validation_rule": None,
            "default_value": "./data/videos",
            "is_system": True,
            "is_active": True
        },
        
        # System Features
        {
            "category": "system_feature",
            "setting_key": "enable_lora_training",
            "setting_value": "true",
            "value_type": "boolean",
            "display_name_cn": "启用LoRA训练",
            "display_name_en": "Enable LoRA Training",
            "description_cn": "是否允许用户进行LoRA模型训练",
            "description_en": "Allow users to train LoRA models",
            "validation_rule": None,
            "default_value": "true",
            "is_system": False,
            "is_active": True
        },
        {
            "category": "system_feature",
            "setting_key": "lora_training_mode",
            "setting_value": "mock",
            "value_type": "string",
            "display_name_cn": "LoRA训练模式",
            "display_name_en": "LoRA Training Mode",
            "description_cn": "训练模式：mock（模拟训练，用于流程验证）或real（真实Kohya训练）",
            "description_en": "Training mode: mock (simulated for workflow validation) or real (real Kohya training)",
            "validation_rule": '{"options": ["mock", "real"]}',
            "default_value": "mock",
            "is_system": False,
            "is_active": True
        },
        {
            "category": "system_feature",
            "setting_key": "enable_quality_assessment",
            "setting_value": "true",
            "value_type": "boolean",
            "display_name_cn": "启用质量评估",
            "display_name_en": "Enable Quality Assessment",
            "description_cn": "训练完成后自动进行质量评估",
            "description_en": "Automatically assess quality after training",
            "validation_rule": None,
            "default_value": "true",
            "is_system": False,
            "is_active": True
        },
        {
            "category": "system_feature",
            "setting_key": "enable_ip_adapter",
            "setting_value": "true",
            "value_type": "boolean",
            "display_name_cn": "启用IP-Adapter",
            "display_name_en": "Enable IP-Adapter",
            "description_cn": "使用IP-Adapter保持角色一致性",
            "description_en": "Use IP-Adapter for character consistency",
            "validation_rule": None,
            "default_value": "true",
            "is_system": False,
            "is_active": True
        },
        {
            "category": "system_feature",
            "setting_key": "enable_celery",
            "setting_value": "true",
            "value_type": "boolean",
            "display_name_cn": "启用Celery异步任务",
            "display_name_en": "Enable Celery Async Tasks",
            "description_cn": "使用Celery处理长时间运行的任务",
            "description_en": "Use Celery for long-running tasks",
            "validation_rule": None,
            "default_value": "true",
            "is_system": False,
            "is_active": True
        }
    ]
    
    async with async_session_factory() as db:
        try:
            # Check if settings already exist
            result = await db.execute(
                text("SELECT COUNT(*) FROM system_settings WHERE is_active=1")
            )
            count = result.scalar()
            
            if count > 0:
                logger.info(f"System settings already initialized ({count} settings found)")
                return
            
            # Create all settings
            for setting_data in settings_data:
                setting = SystemSetting(**setting_data)
                db.add(setting)
            
            await db.commit()
            logger.info(f"Successfully initialized {len(settings_data)} system settings")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to initialize system settings: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(init_system_settings())
