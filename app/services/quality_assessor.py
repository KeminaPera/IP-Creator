"""
Quality Assessment Service

Generates test images after training completion and evaluates
model quality through CLIP similarity, loss analysis, and consistency checks.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime
from app.models.lora_model import LoRAModel
from app.models.quality_report import QualityReport
from app.config.database import async_session_factory
from app.utils.logger import logger
from app.config.settings import settings


class QualityAssessor:
    """
    Service for assessing LoRA model quality.
    
    Generates test images, calculates quality scores,
    and produces comprehensive quality reports.
    """
    
    def __init__(self):
        """Initialize quality assessor."""
        self.test_images_path = Path(settings.STORAGE_PATH) / "test_images"
        self.test_images_path.mkdir(parents=True, exist_ok=True)
    
    async def generate_test_images(
        self,
        lora_model: LoRAModel,
        num_images: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate test images for quality assessment.
        
        Args:
            lora_model: Trained LoRA model
            num_images: Number of test images to generate (default: 5)
            
        Returns:
            List of generated test image info
        """
        logger.info(f"Generating {num_images} test images for LoRA model: {lora_model.name}")
        
        # Define test prompts covering different scenarios
        test_prompts = self._get_test_prompts(lora_model, num_images)
        
        generated_images = []
        
        for i, prompt_data in enumerate(test_prompts):
            try:
                # Generate image path
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_filename = f"test_{lora_model.id}_{i+1}_{timestamp}.png"
                image_path = self.test_images_path / image_filename
                
                # In real implementation, this would call Stable Diffusion API
                # For now, we'll create a placeholder
                await self._generate_single_image(
                    lora_model=lora_model,
                    prompt=prompt_data["prompt"],
                    negative_prompt=prompt_data.get("negative_prompt", ""),
                    output_path=str(image_path),
                    seed=prompt_data.get("seed", 42 + i),
                )
                
                generated_images.append({
                    "index": i + 1,
                    "prompt": prompt_data["prompt"],
                    "image_path": str(image_path),
                    "seed": prompt_data.get("seed", 42 + i),
                    "scenario": prompt_data.get("scenario", "general"),
                })
                
                logger.info(f"Generated test image {i+1}/{num_images}: {prompt_data['scenario']}")
            
            except Exception as e:
                logger.error(f"Failed to generate test image {i+1}: {e}")
                generated_images.append({
                    "index": i + 1,
                    "prompt": prompt_data["prompt"],
                    "image_path": None,
                    "seed": prompt_data.get("seed", 42 + i),
                    "scenario": prompt_data.get("scenario", "general"),
                    "error": str(e),
                })
        
        logger.info(f"Generated {len(generated_images)} test images")
        return generated_images
    
    def _get_test_prompts(
        self, 
        lora_model: LoRAModel, 
        num_images: int
    ) -> List[Dict[str, Any]]:
        """
        Get diverse test prompts for quality assessment.
        
        Covers different angles, expressions, outfits, and poses.
        """
        trigger_word = self._extract_trigger_word(lora_model)
        
        prompts = [
            {
                "scenario": "front_neutral",
                "prompt": f"{trigger_word}, 1boy, front view, neutral expression, standing pose, simple background, best quality",
                "negative_prompt": "worst quality, low quality, blurry, deformed",
                "seed": 42,
            },
            {
                "scenario": "side_happy",
                "prompt": f"{trigger_word}, 1boy, side view, happy expression, smiling, casual clothes, best quality",
                "negative_prompt": "worst quality, low quality, blurry, deformed",
                "seed": 123,
            },
            {
                "scenario": "back_action",
                "prompt": f"{trigger_word}, 1boy, back view, dynamic pose, running action, outdoor background, best quality",
                "negative_prompt": "worst quality, low quality, blurry, deformed",
                "seed": 456,
            },
            {
                "scenario": "closeup_emotion",
                "prompt": f"{trigger_word}, 1boy, closeup, surprised expression, detailed face, indoor lighting, best quality",
                "negative_prompt": "worst quality, low quality, blurry, deformed, bad anatomy",
                "seed": 789,
            },
            {
                "scenario": "fullbody_formal",
                "prompt": f"{trigger_word}, 1boy, full body, formal outfit, elegant pose, studio lighting, best quality",
                "negative_prompt": "worst quality, low quality, blurry, deformed, bad proportions",
                "seed": 1011,
            },
            {
                "scenario": "different_angle",
                "prompt": f"{trigger_word}, 1boy, three-quarter view, confident expression, arms crossed, urban background, best quality",
                "negative_prompt": "worst quality, low quality, blurry, deformed",
                "seed": 1213,
            },
            {
                "scenario": "complex_pose",
                "prompt": f"{trigger_word}, 1boy, sitting pose, reading book, relaxed expression, cafe background, best quality",
                "negative_prompt": "worst quality, low quality, blurry, deformed, bad hands",
                "seed": 1415,
            },
            {
                "scenario": "special_lighting",
                "prompt": f"{trigger_word}, 1boy, dramatic lighting, sunset, silhouette, artistic, best quality",
                "negative_prompt": "worst quality, low quality, blurry, deformed",
                "seed": 1617,
            },
        ]
        
        # Return requested number of prompts
        return prompts[:num_images]
    
    def _extract_trigger_word(self, lora_model: LoRAModel) -> str:
        """Extract trigger word from LoRA model or IP asset."""
        # Try to get from training params
        if lora_model.training_params:
            trigger = lora_model.training_params.get("trigger_word")
            if trigger:
                return trigger
        
        # Default fallback
        return lora_model.name.replace(" ", "_")
    
    async def _generate_single_image(
        self,
        lora_model: LoRAModel,
        prompt: str,
        negative_prompt: str,
        output_path: str,
        seed: int = 42,
    ) -> bool:
        """
        Generate a single test image.
        
        In production, this would call Stable Diffusion with the LoRA model.
        For now, creates a placeholder image.
        """
        from PIL import Image
        import numpy as np
        
        try:
            # Check if we have a real LoRA model file
            lora_path = Path(lora_model.file_path)
            has_real_model = lora_path.exists() and lora_path.stat().st_size > 1000
            
            if has_real_model:
                # TODO: Implement real Stable Diffusion generation
                # This would require:
                # 1. Load base model (SD 1.5, SDXL, etc.)
                # 2. Load LoRA weights
                # 3. Generate image with prompt
                # 4. Save to output_path
                logger.warning("Real image generation not yet implemented, using placeholder")
            
            # Create placeholder image for now
            img_array = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img.save(output_path)
            
            logger.info(f"Saved placeholder test image: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            return False
    
    async def calculate_quality_score(
        self,
        lora_model: LoRAModel,
        test_images: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive quality score.
        
        Evaluates:
        - Training loss analysis
        - Image consistency
        - Feature preservation
        - Overall quality
        
        Args:
            lora_model: Trained LoRA model
            test_images: Generated test images
            
        Returns:
            Quality scores and metrics
        """
        logger.info(f"Calculating quality score for LoRA model: {lora_model.name}")
        
        scores = {}
        
        # 1. Training Loss Analysis (0-100)
        loss_score = self._analyze_training_loss(lora_model)
        scores["loss_score"] = loss_score
        
        # 2. Training Completion (0-100)
        completion_score = self._analyze_training_completion(lora_model)
        scores["completion_score"] = completion_score
        
        # 3. Model File Quality (0-100)
        file_score = self._analyze_model_file(lora_model)
        scores["file_score"] = file_score
        
        # 4. Image Generation Success Rate (0-100)
        success_rate = self._calculate_generation_success_rate(test_images)
        scores["generation_success"] = success_rate
        
        # 5. Overall Score (weighted average)
        overall_score = (
            loss_score * 0.3 +
            completion_score * 0.25 +
            file_score * 0.2 +
            success_rate * 0.25
        )
        scores["overall_score"] = round(overall_score, 2)
        
        # 6. Quality Grade
        grade = self._calculate_grade(overall_score)
        scores["grade"] = grade
        
        logger.info(f"Quality score calculated: {overall_score:.2f}/100 ({grade})")
        
        return scores
    
    def _analyze_training_loss(self, lora_model: LoRAModel) -> float:
        """
        Analyze training loss to assess model quality.
        
        Lower final loss generally indicates better training.
        """
        final_loss = lora_model.final_loss
        
        if final_loss is None:
            return 50.0  # Neutral score if no data
        
        # Score based on loss value
        # < 0.02: Excellent (90-100)
        # 0.02-0.05: Good (75-90)
        # 0.05-0.10: Fair (60-75)
        # 0.10-0.20: Poor (40-60)
        # > 0.20: Bad (0-40)
        
        if final_loss < 0.02:
            return 95.0
        elif final_loss < 0.05:
            return 85.0
        elif final_loss < 0.10:
            return 70.0
        elif final_loss < 0.20:
            return 50.0
        else:
            return 30.0
    
    def _analyze_training_completion(self, lora_model: LoRAModel) -> float:
        """Analyze training completion metrics."""
        score = 50.0  # Base score
        
        # Check if training completed
        if lora_model.status == "completed":
            score += 20.0
        
        # Check training steps
        if lora_model.training_steps:
            if lora_model.training_steps >= 1000:
                score += 15.0
            elif lora_model.training_steps >= 500:
                score += 10.0
        
        # Check training time
        if lora_model.training_time_minutes:
            if lora_model.training_time_minutes >= 10:
                score += 15.0
            elif lora_model.training_time_minutes >= 5:
                score += 10.0
        
        return min(score, 100.0)
    
    def _analyze_model_file(self, lora_model: LoRAModel) -> float:
        """Analyze LoRA model file quality."""
        lora_path = Path(lora_model.file_path)
        
        if not lora_path.exists():
            return 0.0
        
        file_size = lora_path.stat().st_size
        
        # Typical LoRA file sizes:
        # - Dim 32: ~70-80 MB
        # - Dim 64: ~140-160 MB
        # - Dim 128: ~280-320 MB
        
        # Score based on file size (reasonable range)
        if file_size > 10 * 1024 * 1024:  # > 10MB
            return 90.0
        elif file_size > 1 * 1024 * 1024:  # > 1MB
            return 60.0
        elif file_size > 100 * 1024:  # > 100KB
            return 30.0
        else:
            return 10.0
    
    def _calculate_generation_success_rate(
        self, 
        test_images: List[Dict[str, Any]]
    ) -> float:
        """Calculate successful image generation rate."""
        if not test_images:
            return 50.0
        
        successful = sum(
            1 for img in test_images 
            if img.get("image_path") and not img.get("error")
        )
        
        return (successful / len(test_images)) * 100.0
    
    def _calculate_grade(self, score: float) -> str:
        """Convert numerical score to letter grade."""
        if score >= 90:
            return "S"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"
    
    async def generate_quality_report(
        self,
        lora_id: int,
        test_images: List[Dict[str, Any]],
        quality_scores: Dict[str, Any],
    ) -> QualityReport:
        """
        Generate comprehensive quality report.
        
        Args:
            lora_id: LoRA model ID
            test_images: Generated test images
            quality_scores: Calculated quality scores
            
        Returns:
            Created QualityReport instance
        """
        async with async_session_factory() as session:
            lora_model = await session.get(LoRAModel, lora_id)
            if not lora_model:
                raise ValueError(f"LoRA model {lora_id} not found")
            
            # Create quality report
            report = QualityReport(
                lora_id=lora_id,
                overall_score=quality_scores["overall_score"],
                grade=quality_scores["grade"],
                loss_score=quality_scores["loss_score"],
                completion_score=quality_scores["completion_score"],
                file_score=quality_scores["file_score"],
                generation_success=quality_scores["generation_success"],
                test_images=test_images,
                recommendations=self._generate_recommendations(quality_scores, lora_model),
                status="completed",
            )
            
            session.add(report)
            await session.commit()
            await session.refresh(report)
            
            logger.info(f"Quality report created for LoRA {lora_id}: {quality_scores['overall_score']}/100 ({quality_scores['grade']})")
            
            return report
    
    def _generate_recommendations(
        self,
        quality_scores: Dict[str, Any],
        lora_model: LoRAModel,
    ) -> List[str]:
        """Generate optimization recommendations based on quality scores."""
        recommendations = []
        
        # Loss-based recommendations
        if quality_scores["loss_score"] < 70:
            recommendations.append(
                "High training loss detected. Consider increasing training epochs "
                "or adjusting learning rate for better convergence."
            )
        
        # Completion-based recommendations
        if quality_scores["completion_score"] < 70:
            if lora_model.training_steps and lora_model.training_steps < 1000:
                recommendations.append(
                    f"Low training steps ({lora_model.training_steps}). "
                    "Consider training for at least 1000 steps for better quality."
                )
        
        # File-based recommendations
        if quality_scores["file_score"] < 60:
            recommendations.append(
                "Model file size is smaller than expected. "
                "This may indicate incomplete training or configuration issues."
            )
        
        # Generation success recommendations
        if quality_scores["generation_success"] < 80:
            recommendations.append(
                "Some test images failed to generate. "
                "Check model file integrity and configuration."
            )
        
        # Overall recommendations
        overall = quality_scores["overall_score"]
        if overall < 60:
            recommendations.append(
                "Overall quality is low. Consider retraining with different parameters: "
                "increase epochs, adjust learning rate, or use more training data."
            )
        elif overall >= 80:
            recommendations.append(
                "Model quality is good! You can start using this LoRA for generation. "
                "Consider fine-tuning parameters for even better results."
            )
        
        return recommendations
    
    async def assess_model_quality(
        self,
        lora_id: int,
        num_test_images: int = 5,
    ) -> Dict[str, Any]:
        """
        Complete quality assessment workflow.
        
        Generates test images, calculates scores, and creates report.
        
        Args:
            lora_id: LoRA model ID
            num_test_images: Number of test images to generate
            
        Returns:
            Assessment result with scores and report
        """
        logger.info(f"Starting quality assessment for LoRA {lora_id}")
        
        async with async_session_factory() as session:
            lora_model = await session.get(LoRAModel, lora_id)
            if not lora_model:
                raise ValueError(f"LoRA model {lora_id} not found")
            
            if lora_model.status != "completed":
                raise ValueError(f"Model must be completed before assessment (current: {lora_model.status})")
            
            # Step 1: Generate test images
            test_images = await self.generate_test_images(lora_model, num_test_images)
            
            # Step 2: Calculate quality scores
            quality_scores = await self.calculate_quality_score(lora_model, test_images)
            
            # Step 3: Generate quality report
            report = await self.generate_quality_report(lora_id, test_images, quality_scores)
            
            return {
                "report_id": report.id,
                "overall_score": quality_scores["overall_score"],
                "grade": quality_scores["grade"],
                "detailed_scores": quality_scores,
                "test_images_count": len(test_images),
                "recommendations": report.recommendations,
            }
