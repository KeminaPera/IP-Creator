"""
Migration: Create system_settings table and initialize default settings

This migration creates a unified settings table to replace hardcoded
configuration in settings.py with database-driven approach.
"""
import asyncio
from sqlalchemy import text
from app.config.database import get_db_session


async def upgrade():
    """
    Create system_settings table and initialize with default values.
    """
    print("=" * 60)
    print("Creating system_settings table...")
    print("=" * 60)
    
    async for db in get_db_session():
        try:
            # Step 1: Create system_settings table
            print("\n1. Creating system_settings table...")
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category VARCHAR(50) NOT NULL,
                    setting_key VARCHAR(100) NOT NULL,
                    setting_value TEXT,
                    value_type VARCHAR(20) DEFAULT 'string',
                    display_name_cn VARCHAR(100),
                    display_name_en VARCHAR(100),
                    description_cn TEXT,
                    description_en TEXT,
                    validation_rule JSON,
                    default_value TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    is_system BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER,
                    UNIQUE(category, setting_key)
                )
            """))
            
            # Create indexes
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_settings_category 
                ON system_settings(category)
            """))
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_settings_active 
                ON system_settings(is_active)
            """))
            
            print("   ✓ Table created successfully")
            
            # Step 2: Initialize LLM Default Settings
            print("\n2. Initializing LLM default settings...")
            await db.execute(text("""
                INSERT OR IGNORE INTO system_settings 
                (category, setting_key, setting_value, value_type, display_name_cn, display_name_en, default_value, description_cn, description_en)
                VALUES
                ('llm_default', 'temperature', '0.7', 'float', 'LLM 温度', 'LLM Temperature', '0.7', '控制生成文本的创造性，值越高越有创造性', 'Controls creativity of generated text, higher values increase creativity'),
                ('llm_default', 'max_tokens', '2048', 'integer', '最大 Token 数', 'Max Tokens', '2048', 'LLM 生成文本的最大 token 数量', 'Maximum number of tokens for LLM text generation'),
                ('llm_default', 'timeout', '60', 'integer', '超时时间（秒）', 'Timeout (seconds)', '60', 'LLM API 调用超时时间', 'Timeout for LLM API calls')
            """))
            print("   ✓ LLM default settings initialized")
            
            # Step 3: Initialize Resource Limit Settings
            print("\n3. Initializing resource limit settings...")
            await db.execute(text("""
                INSERT OR IGNORE INTO system_settings 
                (category, setting_key, setting_value, value_type, display_name_cn, display_name_en, default_value, validation_rule, description_cn, description_en, is_system)
                VALUES
                ('resource_limit', 'gpu_memory_limit', '6', 'integer', 'GPU 内存限制（GB）', 'GPU Memory Limit (GB)', '6', '{"min": 2, "max": 80}', 'GPU 内存使用上限（GB）', 'GPU memory usage limit in GB', 1),
                ('resource_limit', 'max_concurrent_tasks', '2', 'integer', '最大并发任务数', 'Max Concurrent Tasks', '2', '{"min": 1, "max": 10}', '同时运行的最大任务数量', 'Maximum number of tasks running simultaneously', 1)
            """))
            print("   ✓ Resource limit settings initialized")
            
            # Step 4: Initialize Storage Path Settings
            print("\n4. Initializing storage path settings...")
            await db.execute(text("""
                INSERT OR IGNORE INTO system_settings 
                (category, setting_key, setting_value, value_type, display_name_cn, display_name_en, default_value, description_cn, description_en, is_system)
                VALUES
                ('storage_path', 'storage_path', './data', 'string', '主存储路径', 'Main Storage Path', './data', '项目主数据存储路径', 'Main data storage path for the project', 1),
                ('storage_path', 'models_path', './data/models', 'string', '模型存储路径', 'Models Storage Path', './data/models', 'AI 模型存储路径（Stable Diffusion 等）', 'AI model storage path (Stable Diffusion, etc.)', 1),
                ('storage_path', 'ip_assets_path', './data/ip_assets', 'string', 'IP 资产路径', 'IP Assets Path', './data/ip_assets', 'IP 资产图片存储路径（角色参考图）', 'IP asset images storage path (character references)', 1),
                ('storage_path', 'lora_models_path', './data/lora_models', 'string', 'LoRA 模型路径', 'LoRA Models Path', './data/lora_models', 'LoRA 微调模型存储路径', 'LoRA fine-tuned models storage path', 1),
                ('storage_path', 'videos_path', './data/videos', 'string', '视频存储路径', 'Videos Storage Path', './data/videos', '生成的视频文件存储路径', 'Generated video files storage path', 1)
            """))
            print("   ✓ Storage path settings initialized")
            
            # Step 5: Initialize System Feature Settings
            print("\n5. Initializing system feature settings...")
            await db.execute(text("""
                INSERT OR IGNORE INTO system_settings 
                (category, setting_key, setting_value, value_type, display_name_cn, display_name_en, default_value, description_cn, description_en, is_system)
                VALUES
                ('system_feature', 'lora_training_mode', 'mock', 'string', 'LoRA 训练模式', 'LoRA Training Mode', 'mock', 'LoRA 训练模式：mock（模拟）或 real（真实训练）', 'LoRA training mode: mock (simulated) or real (actual training)', 1),
                ('system_feature', 'enable_model_preload', 'false', 'boolean', '启用模型预下载', 'Enable Model Preload', 'false', '是否在应用启动时预加载模型', 'Whether to preload models on application startup', 0)
            """))
            print("   ✓ System feature settings initialized")
            
            # Commit all changes
            await db.commit()
            
            print("\n" + "=" * 60)
            print("✅ Migration completed successfully!")
            print("=" * 60)
            print("\nSummary:")
            print("  - Table: system_settings created")
            print("  - LLM defaults: 3 settings initialized")
            print("  - Resource limits: 2 settings initialized")
            print("  - Storage paths: 5 settings initialized")
            print("  - System features: 2 settings initialized")
            print("  - Total: 12 settings initialized")
            print("=" * 60)
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(upgrade())
    except Exception as e:
        print(f"Error running migration: {e}")
        import traceback
        traceback.print_exc()
