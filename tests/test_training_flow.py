"""
End-to-end tests for Phase 3: Kohya Training Integration.

Tests the complete training flow including:
- Training configuration validation
- Preset selection
- Custom configuration
- Training start/cancel
- Real-time logging
- Metrics extraction
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
class TestTrainingFlow:
    """Test complete training flow."""

    async def test_get_training_presets(self):
        """Test 1: Get available training presets."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/lora/presets")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            
            presets = data["data"]
            assert len(presets) == 4
            
            # Verify preset names
            preset_names = [p["name"] for p in presets]
            assert "quick_test" in preset_names
            assert "standard" in preset_names
            assert "high_quality" in preset_names
            assert "anime_style" in preset_names
            
            print("✅ Test 1 passed: Training presets retrieved successfully")

    async def test_validate_training_config(self):
        """Test 2: Validate training configuration."""
        valid_config = {
            "base_model": "sd1.5",
            "dataset_id": 1,
            "output_name": "test_lora",
            "epochs": 10,
            "learning_rate": 0.0001,
            "network_dim": 64,
            "batch_size": 1,
            "resolution": 512
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/lora/validate-config",
                json=valid_config
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "valid" in data["data"]
            assert data["data"]["valid"] is True
            
            print("✅ Test 2 passed: Training config validated successfully")

    async def test_validate_invalid_config(self):
        """Test 3: Validate invalid training configuration."""
        invalid_config = {
            "base_model": "sd1.5",
            "dataset_id": 1,
            "output_name": "test_lora",
            "epochs": 200,  # Invalid: > 100
            "learning_rate": 0.0001,
            "network_dim": 64,
            "batch_size": 1,
            "resolution": 512
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/lora/validate-config",
                json=invalid_config
            )
            
            # Should return validation error
            assert response.status_code == 422 or response.status_code == 400
            
            print("✅ Test 3 passed: Invalid config rejected correctly")

    async def test_create_lora_model(self):
        """Test 4: Create a LoRA model."""
        lora_data = {
            "name": "Test LoRA Model",
            "base_model": "sd1.5",
            "description": "Test model for e2e testing",
            "epochs": 10
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/lora/create",
                json=lora_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            
            lora_id = data["data"]["id"]
            assert lora_id is not None
            
            print(f"✅ Test 4 passed: LoRA model created with ID {lora_id}")
            return lora_id

    async def test_start_training_with_preset(self):
        """Test 5: Start training using preset."""
        # First create a model
        lora_id = await self.test_create_lora_model()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Start training with preset
            response = await client.post(
                f"/api/v1/lora/{lora_id}/train",
                json={"use_preset": "quick_test"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "training_started"
            assert data["data"]["config_applied"] is True
            assert "config" in data["data"]
            
            print(f"✅ Test 5 passed: Training started with preset for model {lora_id}")

    async def test_start_training_with_custom_config(self):
        """Test 6: Start training with custom configuration."""
        # First create a model
        lora_id = await self.test_create_lora_model()
        
        custom_config = {
            "base_model": "sd1.5",
            "dataset_id": 1,
            "output_name": "custom_lora",
            "epochs": 5,
            "learning_rate": 0.0002,
            "network_dim": 32,
            "batch_size": 2,
            "resolution": 512
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/lora/{lora_id}/train",
                json={"custom_config": custom_config}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["config"]["custom"] is True
            assert data["data"]["config"]["epochs"] == 5
            
            print(f"✅ Test 6 passed: Training started with custom config for model {lora_id}")

    async def test_get_training_logs(self):
        """Test 7: Get training logs."""
        lora_id = await self.test_create_lora_model()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/lora/{lora_id}/logs",
                params={"limit": 50}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            
            # Logs may be empty for new model
            assert isinstance(data["data"], list)
            
            print(f"✅ Test 7 passed: Training logs retrieved for model {lora_id}")

    async def test_get_training_metrics(self):
        """Test 8: Get training metrics."""
        lora_id = await self.test_create_lora_model()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/lora/{lora_id}/metrics"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            
            metrics = data["data"]
            assert "status" in metrics
            assert "progress" in metrics
            
            print(f"✅ Test 8 passed: Training metrics retrieved for model {lora_id}")

    async def test_cancel_training(self):
        """Test 9: Cancel training."""
        lora_id = await self.test_create_lora_model()
        
        # Start training first
        async with AsyncClient(app=app, base_url="http://test") as client:
            await client.post(
                f"/api/v1/lora/{lora_id}/train",
                json={"use_preset": "quick_test"}
            )
            
            # Cancel training
            response = await client.post(
                f"/api/v1/lora/{lora_id}/cancel"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            print(f"✅ Test 9 passed: Training cancelled for model {lora_id}")

    async def test_delete_lora_model(self):
        """Test 10: Delete LoRA model."""
        lora_id = await self.test_create_lora_model()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.delete(f"/api/v1/lora/{lora_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            print(f"✅ Test 10 passed: LoRA model {lora_id} deleted")


@pytest.mark.asyncio
async def test_complete_training_flow():
    """Integration test: Complete training flow from start to finish."""
    print("\n🚀 Running complete training flow test...")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Create LoRA model
        print("\n📝 Step 1: Creating LoRA model...")
        response = await client.post(
            "/api/v1/lora/create",
            json={
                "name": "Integration Test Model",
                "base_model": "sd1.5",
                "description": "Complete flow test",
                "epochs": 10
            }
        )
        assert response.status_code == 200
        lora_id = response.json()["data"]["id"]
        print(f"   ✅ Created model {lora_id}")
        
        # Step 2: Get presets
        print("\n📋 Step 2: Getting training presets...")
        response = await client.get("/api/v1/lora/presets")
        assert response.status_code == 200
        presets = response.json()["data"]
        print(f"   ✅ Retrieved {len(presets)} presets")
        
        # Step 3: Validate config
        print("\n✓ Step 3: Validating training configuration...")
        response = await client.post(
            "/api/v1/lora/validate-config",
            json={
                "base_model": "sd1.5",
                "dataset_id": 1,
                "output_name": "test_lora",
                "epochs": 10,
                "learning_rate": 0.0001,
                "network_dim": 64,
                "batch_size": 1,
                "resolution": 512
            }
        )
        assert response.status_code == 200
        print("   ✅ Configuration validated")
        
        # Step 4: Start training
        print("\n🚀 Step 4: Starting training...")
        response = await client.post(
            f"/api/v1/lora/{lora_id}/train",
            json={"use_preset": "quick_test"}
        )
        assert response.status_code == 200
        print("   ✅ Training started")
        
        # Step 5: Get logs
        print("\n📄 Step 5: Retrieving training logs...")
        response = await client.get(f"/api/v1/lora/{lora_id}/logs")
        assert response.status_code == 200
        logs = response.json()["data"]
        print(f"   ✅ Retrieved {len(logs)} log entries")
        
        # Step 6: Get metrics
        print("\n📊 Step 6: Retrieving training metrics...")
        response = await client.get(f"/api/v1/lora/{lora_id}/metrics")
        assert response.status_code == 200
        metrics = response.json()["data"]
        print(f"   ✅ Retrieved metrics (status: {metrics['status']})")
        
        # Step 7: Cancel training
        print("\n⏹️ Step 7: Cancelling training...")
        response = await client.post(f"/api/v1/lora/{lora_id}/cancel")
        assert response.status_code == 200
        print("   ✅ Training cancelled")
        
        # Step 8: Cleanup
        print("\n🗑️ Step 8: Cleaning up...")
        response = await client.delete(f"/api/v1/lora/{lora_id}")
        assert response.status_code == 200
        print(f"   ✅ Model {lora_id} deleted")
        
        print("\n🎉 Complete training flow test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
