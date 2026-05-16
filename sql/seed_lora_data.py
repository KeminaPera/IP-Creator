"""
Seed script to insert mock LoRA training data for testing.
Run this after the database is initialized.

Usage:
    python seed_lora_data.py
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

# Database path
DB_PATH = os.path.join("data", "ip_creator.db")


def insert_mock_lora_data():
    """Insert mock LoRA models with various statuses for testing."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🌱 Inserting mock LoRA training data...")
    
    # Mock LoRA models data
    mock_models = [
        {
            "name": "卡通兔子 - 标准训练",
            "file_path": "models/lora/cartoon_rabbit_v1.safetensors",
            "base_model": "sd1.5",
            "status": "completed",
            "final_loss": 0.0156,
            "training_steps": 3000,
            "training_time_minutes": 45.5,
            "weight_default": 0.75,
            "is_active": True,
            "description": "可爱的卡通兔子角色，标准质量训练",
            "training_params": json.dumps({
                "epochs": 10,
                "batch_size": 4,
                "learning_rate": 1e-4,
                "network_dim": 32,
                "network_alpha": 16,
                "optimizer": "adamw8bit"
            })
        },
        {
            "name": "魔法少女 - 高质量",
            "file_path": "models/lora/magical_girl_v2.safetensors",
            "base_model": "sd1.5",
            "status": "completed",
            "final_loss": 0.0089,
            "training_steps": 5000,
            "training_time_minutes": 78.3,
            "weight_default": 0.8,
            "is_active": True,
            "description": "魔法少女角色，高质量精细训练",
            "training_params": json.dumps({
                "epochs": 15,
                "batch_size": 2,
                "learning_rate": 5e-5,
                "network_dim": 64,
                "network_alpha": 32,
                "optimizer": "adamw"
            })
        },
        {
            "name": "科幻机器人 - 训练中",
            "file_path": "models/lora/scifi_robot_v1.safetensors",
            "base_model": "sdxl",
            "status": "training",
            "final_loss": None,
            "training_steps": 1850,
            "training_time_minutes": None,
            "weight_default": 0.7,
            "is_active": True,
            "description": "科幻风格机器人，正在训练中...",
            "training_params": json.dumps({
                "epochs": 20,
                "batch_size": 2,
                "learning_rate": 1e-4,
                "network_dim": 32,
                "network_alpha": 16,
                "optimizer": "adamw8bit"
            })
        },
        {
            "name": "Q版猫咪 - 快速测试",
            "file_path": "models/lora/chibi_cat_v1.safetensors",
            "base_model": "sd1.5",
            "status": "completed",
            "final_loss": 0.0234,
            "training_steps": 500,
            "training_time_minutes": 8.2,
            "weight_default": 0.65,
            "is_active": True,
            "description": "Q版猫咪角色，快速测试训练",
            "training_params": json.dumps({
                "epochs": 2,
                "batch_size": 8,
                "learning_rate": 2e-4,
                "network_dim": 16,
                "network_alpha": 8,
                "optimizer": "adamw8bit"
            })
        },
        {
            "name": "古风剑客 - 待训练",
            "file_path": "models/lora/ancient_swordsman_v1.safetensors",
            "base_model": "sd1.5",
            "status": "pending",
            "final_loss": None,
            "training_steps": 0,
            "training_time_minutes": None,
            "weight_default": 0.7,
            "is_active": True,
            "description": "古风武侠剑客，准备开始训练",
            "training_params": json.dumps({
                "epochs": 10,
                "batch_size": 4,
                "learning_rate": 1e-4,
                "network_dim": 32,
                "network_alpha": 16,
                "optimizer": "adamw8bit"
            })
        },
        {
            "name": "机甲战士 - 训练失败",
            "file_path": "models/lora/mecha_warrior_v1.safetensors",
            "base_model": "sdxl",
            "status": "failed",
            "final_loss": None,
            "training_steps": 450,
            "training_time_minutes": 12.5,
            "weight_default": 0.7,
            "is_active": False,
            "description": "机甲战士角色，训练过程中断",
            "error_message": "CUDA out of memory. Tried to allocate 2.50 GiB",
            "training_params": json.dumps({
                "epochs": 20,
                "batch_size": 4,
                "learning_rate": 1e-4,
                "network_dim": 64,
                "network_alpha": 32,
                "optimizer": "adamw"
            })
        }
    ]
    
    # Insert LoRA models
    for model in mock_models:
        cursor.execute("""
            INSERT INTO lora_models (
                name, file_path, base_model, status, final_loss,
                training_steps, training_time_minutes, weight_default,
                is_active, description, error_message, training_params
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model["name"],
            model["file_path"],
            model["base_model"],
            model["status"],
            model.get("final_loss"),
            model.get("training_steps", 0),
            model.get("training_time_minutes"),
            model.get("weight_default", 0.7),
            model.get("is_active", True),
            model.get("description", ""),
            model.get("error_message"),
            model.get("training_params", "{}")
        ))
    
    print(f"✅ Inserted {len(mock_models)} LoRA models")
    
    # Get the inserted model IDs
    cursor.execute("SELECT id, name, status FROM lora_models ORDER BY id DESC LIMIT 10")
    inserted_models = cursor.fetchall()
    
    print("\n📊 Inserted LoRA Models:")
    print("-" * 60)
    for model_id, name, status in inserted_models:
        status_icon = {
            "completed": "✅",
            "training": "🔄",
            "pending": "⏳",
            "failed": "❌"
        }.get(status, "❓")
        print(f"{status_icon} ID {model_id}: {name} [{status}]")
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print("\n🎉 Mock data insertion completed!")
    print("\n💡 You can now:")
    print("   1. Visit http://localhost:5173")
    print("   2. Navigate to 'LoRA 模型' page")
    print("   3. See the mock data in the table")
    print("   4. Click '监控' on the training model")
    print("   5. Click '启动训练' on pending models")


if __name__ == "__main__":
    insert_mock_lora_data()
