"""
Unit tests for DatasetGenerator service.

Tests dataset generation from IP features and validation logic.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.dataset_generator import DatasetGenerator
from app.models.training_dataset import TrainingDataset
from app.models.ip_asset import IPAsset


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.get = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def generator(mock_db_session):
    """Create DatasetGenerator instance."""
    return DatasetGenerator(db=mock_db_session)


@pytest.fixture
def mock_ip_asset():
    """Create a mock IP asset."""
    ip = MagicMock(spec=IPAsset)
    ip.id = 1
    ip.name = "Test Character"
    ip.description = "A test character for dataset generation"
    return ip


class TestDatasetGeneration:
    """Test dataset generation from features."""
    
    @pytest.mark.asyncio
    async def test_generate_dataset_from_features(self, generator, mock_db_session, mock_ip_asset):
        """Test successful dataset generation."""
        # Mock IP asset retrieval
        mock_db_session.get.return_value = mock_ip_asset
        
        # Mock feature loading
        with patch.object(generator, '_load_features', new_callable=AsyncMock) as mock_load:
            mock_load.return_value = [
                {"id": 1, "type": "outfit", "name": "Casual", "images": ["/path/img1.jpg"]},
                {"id": 2, "type": "expression", "name": "Happy", "images": ["/path/img2.jpg"]}
            ]
            
            # Mock combination calculation
            with patch.object(generator, '_calculate_combinations') as mock_calc:
                mock_calc.return_value = [
                    {"outfit": 1, "expression": 2},
                    {"outfit": 1, "expression": 2}
                ]
                
                # Mock caption generation
                with patch.object(generator, '_generate_caption') as mock_caption:
                    mock_caption.return_value = "Test character, casual outfit, happy expression"
                    
                    # Execute
                    selected_features = {
                        "outfit": [1],
                        "expression": [2]
                    }
                    
                    result = await generator.generate_dataset_from_features(
                        ip_asset_id=1,
                        selected_features=selected_features,
                        dataset_name="Test Dataset",
                        description="Test description"
                    )
                    
                    # Verify
                    assert isinstance(result, TrainingDataset)
                    assert result.name == "Test Dataset"
                    assert result.image_count == 2
                    assert result.status == "pending"
                    
                    # Verify DB interactions
                    assert mock_db_session.add.called
                    assert mock_db_session.flush.called
    
    @pytest.mark.asyncio
    async def test_generate_dataset_ip_not_found(self, generator, mock_db_session):
        """Test dataset generation with non-existent IP."""
        mock_db_session.get.return_value = None
        
        with pytest.raises(ValueError, match="IP asset .* not found"):
            await generator.generate_dataset_from_features(
                ip_asset_id=999,
                selected_features={"outfit": [1]},
                dataset_name="Test Dataset"
            )


class TestCaptionGeneration:
    """Test caption generation logic."""
    
    def test_generate_caption_basic(self, generator, mock_ip_asset):
        """Test basic caption generation."""
        combination = {
            "outfit": {"name": "Casual Outfit"},
            "expression": {"name": "Happy"},
            "pose": {"name": "Standing"}
        }
        
        caption = generator._generate_caption(mock_ip_asset, combination)
        
        assert isinstance(caption, str)
        assert len(caption) > 0
        # Should include feature names
        assert "Casual Outfit" in caption or "Happy" in caption or "Standing" in caption
    
    def test_generate_caption_partial(self, generator, mock_ip_asset):
        """Test caption with partial features."""
        combination = {
            "outfit": {"name": "Formal Wear"}
        }
        
        caption = generator._generate_caption(mock_ip_asset, combination)
        
        assert isinstance(caption, str)
        assert "Formal Wear" in caption


class TestCombinationCalculation:
    """Test feature combination calculation."""
    
    def test_calculate_combinations_single_feature(self, generator):
        """Test combinations with single feature type."""
        feature_data = {
            "outfit": [
                {"id": 1, "name": "Casual"},
                {"id": 2, "name": "Formal"}
            ]
        }
        
        combinations = generator._calculate_combinations(feature_data)
        
        assert len(combinations) == 2
    
    def test_calculate_combinations_multiple_features(self, generator):
        """Test combinations with multiple feature types."""
        feature_data = {
            "outfit": [{"id": 1, "name": "Casual"}],
            "expression": [
                {"id": 2, "name": "Happy"},
                {"id": 3, "name": "Sad"}
            ]
        }
        
        combinations = generator._calculate_combinations(feature_data)
        
        # Should be cartesian product: 1 outfit × 2 expressions = 2 combinations
        assert len(combinations) == 2
    
    def test_calculate_combinations_empty(self, generator):
        """Test combinations with empty feature data."""
        feature_data = {}
        
        combinations = generator._calculate_combinations(feature_data)
        
        assert len(combinations) == 0


class TestFeatureLoading:
    """Test feature loading from database."""
    
    @pytest.mark.asyncio
    async def test_load_features_success(self, generator, mock_db_session):
        """Test successful feature loading."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(id=1, name="Feature 1"),
            MagicMock(id=2, name="Feature 2")
        ]
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        features = await generator._load_features([1, 2], "outfit")
        
        assert len(features) == 2
        assert mock_db_session.execute.called
    
    @pytest.mark.asyncio
    async def test_load_features_empty(self, generator, mock_db_session):
        """Test loading with no feature IDs."""
        features = await generator._load_features([], "outfit")
        
        assert features == []


class TestDatasetValidation:
    """Test dataset validation logic."""
    
    @pytest.mark.asyncio
    async def test_validate_dataset_sufficient_images(self, generator):
        """Test validation with sufficient images."""
        # This would test the validation logic if it exists in dataset_generator
        # For now, we're testing that the generator creates valid datasets
        pass
    
    def test_dataset_image_count_calculation(self, generator):
        """Test that image count is calculated correctly."""
        # Test that combinations are counted properly
        feature_data = {
            "outfit": [1, 2],  # 2 outfits
            "expression": [3, 4, 5],  # 3 expressions
            "pose": [6]  # 1 pose
        }
        
        combinations = generator._calculate_combinations(feature_data)
        
        # Should be 2 × 3 × 1 = 6 combinations
        assert len(combinations) == 6


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_generate_dataset_with_no_features(self, generator, mock_db_session, mock_ip_asset):
        """Test dataset generation with no selected features."""
        mock_db_session.get.return_value = mock_ip_asset
        
        with patch.object(generator, '_calculate_combinations') as mock_calc:
            mock_calc.return_value = []
            
            result = await generator.generate_dataset_from_features(
                ip_asset_id=1,
                selected_features={},
                dataset_name="Empty Dataset"
            )
            
            assert result.image_count == 0
    
    @pytest.mark.asyncio
    async def test_generate_dataset_large_combinations(self, generator, mock_db_session, mock_ip_asset):
        """Test dataset generation with many combinations."""
        mock_db_session.get.return_value = mock_ip_asset
        
        # Simulate large combination count
        with patch.object(generator, '_calculate_combinations') as mock_calc:
            # Create 100 combinations
            mock_calc.return_value = [{"outfit": i, "expression": j} 
                                     for i in range(10) 
                                     for j in range(10)]
            
            with patch.object(generator, '_generate_caption') as mock_caption:
                mock_caption.return_value = "Test caption"
                
                result = await generator.generate_dataset_from_features(
                    ip_asset_id=1,
                    selected_features={"outfit": list(range(10)), "expression": list(range(10))},
                    dataset_name="Large Dataset"
                )
                
                assert result.image_count == 100
