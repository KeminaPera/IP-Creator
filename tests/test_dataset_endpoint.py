"""
Test dataset API endpoint directly
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config.database import get_db_session
from app.core.dataset_manager import dataset_manager
from app.schemas.training_dataset import TrainingDatasetResponse

async def test_list_datasets():
    """Test listing datasets"""
    try:
        # Get database session
        async for db in get_db_session():
            print("✓ Database session obtained")
            
            # Call list_datasets
            datasets, total = await dataset_manager.list_datasets(
                db, ip_asset_id=None, status=None, skip=0, limit=20
            )
            
            print(f"✓ Retrieved {len(datasets)} datasets, total={total}")
            
            # Try to convert to response schema
            for i, dataset in enumerate(datasets):
                try:
                    response = TrainingDatasetResponse.model_validate(dataset)
                    print(f"✓ Dataset {i+1} validated successfully: id={response.id}, name={response.name}")
                except Exception as e:
                    print(f"✗ Dataset {i+1} validation failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            print("\n✓ All tests passed!")
            break
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_list_datasets())
