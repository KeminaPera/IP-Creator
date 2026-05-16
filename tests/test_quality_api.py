"""Test quality grade API response"""
import asyncio
from app.config.database import AsyncSessionLocal
from sqlalchemy import text

async def test():
    async with AsyncSessionLocal() as session:
        # Get LoRA models
        result = await session.execute(text('SELECT id, name FROM lora_models LIMIT 3'))
        loras = result.fetchall()
        print("LoRA Models:")
        for lora in loras:
            print(f"  - ID: {lora[0]}, Name: {lora[1]}")
        
        # Get quality reports
        result = await session.execute(text('SELECT lora_id, grade, overall_score FROM quality_reports'))
        reports = result.fetchall()
        print("\nQuality Reports:")
        for report in reports:
            print(f"  - LoRA ID: {report[0]}, Grade: {report[1]}, Score: {report[2]}")

asyncio.run(test())
