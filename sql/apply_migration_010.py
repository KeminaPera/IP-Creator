#!/usr/bin/env python3
"""直接执行SQLite迁移"""
import sqlite3
import sys
from pathlib import Path

# 数据库路径
db_path = Path(__file__).parent / "data" / "ip_creator.db"

if not db_path.exists():
    print(f"❌ 数据库文件不存在: {db_path}")
    sys.exit(1)

print(f"📂 数据库路径: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 检查列是否存在
    cursor.execute("PRAGMA table_info(quality_reports)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'training_diagnosis' in columns:
        print("✅ training_diagnosis 列已存在，无需迁移")
    else:
        # 添加列
        sql = "ALTER TABLE quality_reports ADD COLUMN training_diagnosis TEXT NULL"
        cursor.execute(sql)
        conn.commit()
        print("✅ 迁移 010 执行成功")
        print("   已添加 training_diagnosis 列到 quality_reports 表")
    
    # 验证
    cursor.execute("PRAGMA table_info(quality_reports)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"\n📋 quality_reports 表当前有 {len(columns)} 个字段")
    
    conn.close()
    
except Exception as e:
    print(f"❌ 迁移失败: {e}")
    sys.exit(1)
