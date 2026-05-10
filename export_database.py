"""
Export all database tables to JSON files in the data directory.

This script exports all table data from the SQLite database to JSON files
for backup, analysis, or migration purposes.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy import select, inspect
from app.config.database import get_db_session, engine
from app.models.llm_provider import LLMProvider, LLMModel
from app.models.llm_model import LLMConfig
from app.models.ip_asset import IPAsset
from app.models.lora_model import LoRAModel
from app.models.task import TaskRecord
from app.models.user import User
from app.utils.logger import logger


# Define all models to export
MODELS_TO_EXPORT = [
    ("llm_providers", LLMProvider),
    ("llm_models", LLMModel),
    ("llm_configs", LLMConfig),
    ("ip_assets", IPAsset),
    ("lora_models", LoRAModel),
    ("task_records", TaskRecord),
    ("users", User),
]


def serialize_value(value):
    """Serialize a value to JSON-compatible format."""
    if isinstance(value, datetime):
        return value.isoformat()
    elif hasattr(value, '__dict__'):
        # Handle SQLAlchemy model instances
        return str(value)
    return value


def model_to_dict(model_instance):
    """Convert a SQLAlchemy model instance to a dictionary."""
    result = {}
    for column in model_instance.__table__.columns:
        value = getattr(model_instance, column.name)
        result[column.name] = serialize_value(value)
    return result


async def export_all_tables():
    """Export all database tables to JSON files."""
    print("=" * 80)
    print("Exporting Database Tables to JSON")
    print("=" * 80)
    
    # Create export directory
    export_dir = Path("./data/exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    
    total_tables = 0
    total_records = 0
    
    async for db in get_db_session():
        try:
            for table_name, model_class in MODELS_TO_EXPORT:
                print(f"\nExporting {table_name}...")
                
                try:
                    # Query all records
                    result = await db.execute(select(model_class))
                    records = result.scalars().all()
                    
                    # Convert to dictionaries
                    data = [model_to_dict(record) for record in records]
                    
                    # Write to JSON file
                    output_file = export_dir / f"{table_name}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    record_count = len(data)
                    total_records += record_count
                    total_tables += 1
                    
                    print(f"  ✓ Exported {record_count} records to {output_file}")
                    
                except Exception as e:
                    print(f"  ✗ Error exporting {table_name}: {e}")
                    logger.error(f"Error exporting {table_name}: {e}")
            
            await db.commit()
            
        except Exception as e:
            await db.rollback()
            print(f"\n✗ Error during export: {e}")
            logger.error(f"Error during export: {e}")
            raise
        finally:
            await db.close()
    
    # Create a summary file
    summary = {
        "export_date": datetime.now().isoformat(),
        "total_tables": total_tables,
        "total_records": total_records,
        "tables": {
            table_name: {
                "model": model_class.__name__,
                "file": f"{table_name}.json"
            }
            for table_name, model_class in MODELS_TO_EXPORT
        }
    }
    
    summary_file = export_dir / "export_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 80)
    print("Export Summary:")
    print(f"  Total Tables Exported: {total_tables}")
    print(f"  Total Records Exported: {total_records}")
    print(f"  Export Directory: {export_dir.absolute()}")
    print(f"  Summary File: {summary_file}")
    print("=" * 80)


async def export_specific_table(table_name: str):
    """Export a specific table to JSON."""
    print(f"\nExporting {table_name}...")
    
    export_dir = Path("./data/exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    
    # Find the model class for this table
    model_class = None
    for name, model in MODELS_TO_EXPORT:
        if name == table_name:
            model_class = model
            break
    
    if not model_class:
        print(f"✗ Table '{table_name}' not found in export list")
        return
    
    async for db in get_db_session():
        try:
            result = await db.execute(select(model_class))
            records = result.scalars().all()
            data = [model_to_dict(record) for record in records]
            
            output_file = export_dir / f"{table_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ Exported {len(data)} records to {output_file}")
            
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"✗ Error: {e}")
            raise
        finally:
            await db.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Export specific table
        table_name = sys.argv[1]
        asyncio.run(export_specific_table(table_name))
    else:
        # Export all tables
        asyncio.run(export_all_tables())
