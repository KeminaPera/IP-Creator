"""
Unit tests for QualityAssessor service.

Tests overfitting/underfitting detection and quality scoring.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.quality_assessor import QualityAssessor
from app.models.lora_model import LoRAModel


@pytest.fixture
def mock_lora_model():
    """Create a mock LoRA model for testing."""
    model = MagicMock(spec=LoRAModel)
    model.id = 1
    model.name = "Test LoRA"
    model.status = "completed"
    model.final_loss = 0.05
    model.training_steps = 1500
    model.training_time_minutes = 30
    model.dataset_id = 1
    model.file_path = "/tmp/test_lora.safetensors"
    return model


@pytest.fixture
def assessor():
    """Create QualityAssessor instance."""
    return QualityAssessor()


class TestOverfittingDetection:
    """Test overfitting detection logic."""
    
    @pytest.mark.asyncio
    async def test_detect_overfitting_severe(self, assessor, mock_lora_model):
        """Test severe overfitting detection (loss increases >50%)."""
        # Mock training logger to return loss curve with U-shape
        with patch('app.services.training_logger.training_logger') as mock_logger:
            mock_logger.get_metrics = AsyncMock(return_value={
                "losses": [0.2, 0.15, 0.1, 0.05, 0.03, 0.04, 0.06, 0.08],
                "epochs": [1, 2, 3, 4, 5, 6, 7, 8]
            })
            
            result = await assessor.detect_overfitting(mock_lora_model)
            
            assert result["is_overfitting"] is True
            assert result["severity"] == "severe"
            assert result["confidence"] > 0.5
            assert len(result["indicators"]) > 0
            assert len(result["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_detect_overfitting_mild(self, assessor, mock_lora_model):
        """Test mild overfitting detection (loss increases 5-20%)."""
        with patch('app.services.training_logger.training_logger') as mock_logger:
            mock_logger.get_metrics = AsyncMock(return_value={
                "losses": [0.2, 0.15, 0.1, 0.05, 0.04, 0.045, 0.048],
                "epochs": [1, 2, 3, 4, 5, 6, 7]
            })
            
            result = await assessor.detect_overfitting(mock_lora_model)
            
            assert result["is_overfitting"] is True
            assert result["severity"] in ["mild", "moderate"]
    
    @pytest.mark.asyncio
    async def test_no_overfitting(self, assessor, mock_lora_model):
        """Test healthy training (loss consistently decreases)."""
        with patch('app.services.training_logger.training_logger') as mock_logger:
            mock_logger.get_metrics = AsyncMock(return_value={
                "losses": [0.2, 0.15, 0.12, 0.1, 0.08, 0.06, 0.05, 0.04],
                "epochs": [1, 2, 3, 4, 5, 6, 7, 8]
            })
            
            result = await assessor.detect_overfitting(mock_lora_model)
            
            assert result["is_overfitting"] is False
            assert result["severity"] == "none"
    
    @pytest.mark.asyncio
    async def test_overfitting_high_steps_per_image(self, assessor, mock_lora_model):
        """Test overfitting detection based on high training ratio."""
        with patch('app.services.training_logger.training_logger') as mock_logger:
            mock_logger.get_metrics = AsyncMock(return_value={
                "losses": [0.2, 0.15, 0.1, 0.08, 0.07]
            })
            
            # Mock dataset with few images
            with patch('app.services.quality_assessor.async_session_factory') as mock_session:
                mock_dataset = MagicMock()
                mock_dataset.image_count = 5  # Very small dataset
                mock_session.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_dataset)
                
                # High training steps relative to dataset size
                mock_lora_model.training_steps = 2000
                
                result = await assessor.detect_overfitting(mock_lora_model)
                
                # Should detect overfitting due to high steps/image ratio
                assert "indicators" in result
                assert any("steps/image" in ind for ind in result["indicators"])


class TestUnderfittingDetection:
    """Test underfitting detection logic."""
    
    @pytest.mark.asyncio
    async def test_detect_underfitting_severe(self, assessor, mock_lora_model):
        """Test severe underfitting (loss barely decreases)."""
        with patch('app.services.training_logger.training_logger') as mock_logger:
            mock_logger.get_metrics = AsyncMock(return_value={
                "losses": [0.2, 0.19, 0.185, 0.18, 0.175, 0.17],
                "epochs": [1, 2, 3, 4, 5, 6]
            })
            
            result = await assessor.detect_underfitting(mock_lora_model)
            
            assert result["is_underfitting"] is True
            assert result["severity"] == "severe"
            assert result["confidence"] >= 0.7
    
    @pytest.mark.asyncio
    async def test_detect_underfitting_few_steps(self, assessor, mock_lora_model):
        """Test underfitting due to too few training steps."""
        with patch('app.services.training_logger.training_logger') as mock_logger:
            mock_logger.get_metrics = AsyncMock(return_value={
                "losses": [0.2, 0.15, 0.12, 0.1]
            })
            
            mock_lora_model.training_steps = 300  # Too few
            
            result = await assessor.detect_underfitting(mock_lora_model)
            
            assert result["is_underfitting"] is True
            assert any("training steps" in ind.lower() for ind in result["indicators"])
    
    @pytest.mark.asyncio
    async def test_no_underfitting(self, assessor, mock_lora_model):
        """Test healthy training (good loss reduction)."""
        with patch('app.services.training_logger.training_logger') as mock_logger:
            mock_logger.get_metrics = AsyncMock(return_value={
                "losses": [0.2, 0.15, 0.1, 0.06, 0.04, 0.03],
                "epochs": [1, 2, 3, 4, 5, 6]
            })
            
            mock_lora_model.training_steps = 1500
            mock_lora_model.final_loss = 0.03
            
            result = await assessor.detect_underfitting(mock_lora_model)
            
            assert result["is_underfitting"] is False
            assert result["severity"] == "none"


class TestTrainingDiagnosis:
    """Test comprehensive training diagnosis."""
    
    @pytest.mark.asyncio
    async def test_healthy_diagnosis(self, assessor, mock_lora_model):
        """Test healthy training diagnosis."""
        with patch.object(assessor, 'detect_overfitting', new_callable=AsyncMock) as mock_overfit:
            mock_overfit.return_value = {
                "is_overfitting": False,
                "severity": "none",
                "confidence": 0.0,
                "indicators": [],
                "recommendations": []
            }
            
            with patch.object(assessor, 'detect_underfitting', new_callable=AsyncMock) as mock_underfit:
                mock_underfit.return_value = {
                    "is_underfitting": False,
                    "severity": "none",
                    "confidence": 0.0,
                    "indicators": [],
                    "recommendations": []
                }
                
                result = await assessor.generate_training_diagnosis(mock_lora_model)
                
                assert result["overall_status"] == "healthy"
                assert result["primary_issue"] == "none"
                assert result["can_use_model"] is True
    
    @pytest.mark.asyncio
    async def test_overfitting_diagnosis(self, assessor, mock_lora_model):
        """Test overfitting diagnosis."""
        with patch.object(assessor, 'detect_overfitting', new_callable=AsyncMock) as mock_overfit:
            mock_overfit.return_value = {
                "is_overfitting": True,
                "severity": "moderate",
                "confidence": 0.7,
                "indicators": ["Loss increased by 30%"],
                "recommendations": ["Reduce epochs"]
            }
            
            with patch.object(assessor, 'detect_underfitting', new_callable=AsyncMock) as mock_underfit:
                mock_underfit.return_value = {
                    "is_underfitting": False,
                    "severity": "none",
                    "confidence": 0.0,
                    "indicators": [],
                    "recommendations": []
                }
                
                result = await assessor.generate_training_diagnosis(mock_lora_model)
                
                assert result["overall_status"] == "overfitting"
                assert result["primary_issue"] == "overfitting"
                assert len(result["recommendations"]) > 0


class TestQualityScoring:
    """Test quality scoring methods."""
    
    def test_analyze_training_loss_excellent(self, assessor, mock_lora_model):
        """Test loss scoring for excellent training."""
        mock_lora_model.final_loss = 0.015
        score = assessor._analyze_training_loss(mock_lora_model)
        assert score >= 90.0
    
    def test_analyze_training_loss_good(self, assessor, mock_lora_model):
        """Test loss scoring for good training."""
        mock_lora_model.final_loss = 0.03
        score = assessor._analyze_training_loss(mock_lora_model)
        assert 75.0 <= score < 90.0
    
    def test_analyze_training_loss_poor(self, assessor, mock_lora_model):
        """Test loss scoring for poor training."""
        mock_lora_model.final_loss = 0.15
        score = assessor._analyze_training_loss(mock_lora_model)
        assert 40.0 <= score < 60.0
    
    def test_analyze_training_loss_no_data(self, assessor, mock_lora_model):
        """Test loss scoring with no data."""
        mock_lora_model.final_loss = None
        score = assessor._analyze_training_loss(mock_lora_model)
        assert score == 50.0
    
    def test_calculate_grade(self, assessor):
        """Test grade calculation."""
        assert assessor._calculate_grade(95) == "S"
        assert assessor._calculate_grade(85) == "A"
        assert assessor._calculate_grade(75) == "B"
        assert assessor._calculate_grade(65) == "C"
        assert assessor._calculate_grade(55) == "D"
        assert assessor._calculate_grade(40) == "F"
    
    def test_generation_success_rate(self, assessor):
        """Test generation success rate calculation."""
        test_images = [
            {"image_path": "/path/1.png", "error": None},
            {"image_path": "/path/2.png", "error": None},
            {"image_path": None, "error": "Failed"},
            {"image_path": "/path/4.png", "error": None},
        ]
        
        rate = assessor._calculate_generation_success_rate(test_images)
        assert rate == 75.0
    
    def test_generation_success_rate_empty(self, assessor):
        """Test generation success rate with no images."""
        rate = assessor._calculate_generation_success_rate([])
        assert rate == 50.0


class TestRecommendations:
    """Test recommendation generation."""
    
    def test_recommendations_for_poor_loss(self, assessor, mock_lora_model):
        """Test recommendations for high training loss."""
        quality_scores = {
            "loss_score": 50.0,
            "completion_score": 80.0,
            "file_score": 90.0,
            "generation_success": 100.0,
            "overall_score": 70.0
        }
        
        recommendations = assessor._generate_recommendations(quality_scores, mock_lora_model)
        
        assert any("training loss" in rec.lower() for rec in recommendations)
    
    def test_recommendations_for_low_steps(self, assessor, mock_lora_model):
        """Test recommendations for low training steps."""
        mock_lora_model.training_steps = 500
        
        quality_scores = {
            "loss_score": 80.0,
            "completion_score": 60.0,
            "file_score": 90.0,
            "generation_success": 100.0,
            "overall_score": 75.0
        }
        
        recommendations = assessor._generate_recommendations(quality_scores, mock_lora_model)
        
        assert any("training steps" in rec.lower() for rec in recommendations)
    
    def test_recommendations_for_good_model(self, assessor, mock_lora_model):
        """Test recommendations for good quality model."""
        quality_scores = {
            "loss_score": 90.0,
            "completion_score": 90.0,
            "file_score": 90.0,
            "generation_success": 100.0,
            "overall_score": 92.0
        }
        
        recommendations = assessor._generate_recommendations(quality_scores, mock_lora_model)
        
        assert any("good" in rec.lower() for rec in recommendations)
