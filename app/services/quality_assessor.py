"""
Quality Assessment Service

Generates test images after training completion and evaluates
model quality through CLIP similarity, loss analysis, and consistency checks.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from app.utils.time_utils import get_timestamp_filename
from app.models.lora_model import LoRAModel
from app.models.quality_report import QualityReport
from app.config.database import async_session_factory
from app.utils.logger import logger
from app.config.settings import settings
from app.services.sd_image_generator import SDImageGenerator
from app.services.clip_similarity import CLIPSimilarityCalculator


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
        self.sd_generator = SDImageGenerator()
        self.clip_calculator = CLIPSimilarityCalculator()
    
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
                timestamp = get_timestamp_filename()
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
        Generate a single test image using Stable Diffusion.
        
        Args:
            lora_model: Trained LoRA model
            prompt: Generation prompt
            negative_prompt: Negative prompt
            output_path: Path to save the image
            seed: Random seed
            
        Returns:
            True if generation succeeded
        """
        try:
            # Get LoRA path
            lora_path = lora_model.file_path if Path(lora_model.file_path).exists() else None
            
            # Generate image using SD
            result = await self.sd_generator.generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                lora_path=lora_path,
                lora_weight=0.8,
                seed=seed,
                width=512,
                height=512,
                steps=20,
                cfg_scale=7.0,
                output_path=output_path,
            )
            
            if result["success"]:
                logger.info(f"Generated test image: {result.get('backend', 'unknown')} backend")
                return True
            else:
                logger.error(f"Failed to generate image: {result.get('error')}")
                return False
        
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
        - Image consistency (CLIP similarity)
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
        
        # 5. CLIP Character Consistency (0-100) - NEW!
        clip_score = await self._calculate_clip_consistency(lora_model, test_images)
        scores["clip_consistency"] = clip_score
        
        # 6. Overall Score (weighted average)
        overall_score = (
            loss_score * 0.25 +
            completion_score * 0.20 +
            file_score * 0.15 +
            success_rate * 0.20 +
            clip_score * 0.20  # CLIP contributes 20%
        )
        scores["overall_score"] = round(overall_score, 2)
        
        # 7. Quality Grade
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
    
    async def detect_overfitting(self, lora_model: LoRAModel) -> Dict[str, Any]:
        """
        Detect overfitting in trained LoRA model.
        
        Analyzes:
        - Loss curve patterns (U-shape indicates overfitting)
        - Training epochs vs dataset size ratio
        - Final loss vs minimum loss divergence
        
        Args:
            lora_model: Trained LoRA model
            
        Returns:
            Detection result with severity and recommendations
        """
        result = {
            "is_overfitting": False,
            "severity": "none",  # none, mild, moderate, severe
            "confidence": 0.0,
            "indicators": [],
            "recommendations": []
        }
        
        try:
            # Get training metrics (loss curve)
            from app.services.training_logger import training_logger
            metrics = await training_logger.get_metrics(lora_model.id)
            losses = metrics.get("losses", [])
            
            # Indicator 1: Loss curve analysis
            if len(losses) >= 10:
                # Check for U-shape pattern (loss decreases then increases)
                min_loss_idx = losses.index(min(losses))
                min_loss_position = min_loss_idx / len(losses)
                
                # If minimum loss occurs in first 60% of training, likely overfitting
                if min_loss_position < 0.6:
                    # Calculate how much loss increased after minimum
                    final_loss = losses[-1]
                    min_loss = losses[min_loss_idx]
                    
                    if min_loss > 0:
                        loss_increase_ratio = (final_loss - min_loss) / min_loss
                        
                        if loss_increase_ratio > 0.5:  # 50% increase
                            result["is_overfitting"] = True
                            result["severity"] = "severe"
                            result["confidence"] = min(loss_increase_ratio / 2.0, 1.0)
                            result["indicators"].append(
                                f"Loss increased by {loss_increase_ratio*100:.1f}% after reaching minimum "
                                f"at epoch {min_loss_idx + 1}"
                            )
                            result["recommendations"].append(
                                "Reduce training epochs by 30-40% to prevent overfitting"
                            )
                        elif loss_increase_ratio > 0.2:  # 20% increase
                            result["is_overfitting"] = True
                            result["severity"] = "moderate"
                            result["confidence"] = 0.7
                            result["indicators"].append(
                                f"Loss increased by {loss_increase_ratio*100:.1f}% after minimum"
                            )
                            result["recommendations"].append(
                                "Consider reducing epochs or adding regularization"
                            )
                        elif loss_increase_ratio > 0.05:  # 5% increase
                            result["is_overfitting"] = True
                            result["severity"] = "mild"
                            result["confidence"] = 0.5
                            result["indicators"].append(
                                f"Slight loss increase ({loss_increase_ratio*100:.1f}%) detected"
                            )
                            result["recommendations"].append(
                                "Monitor quality, consider early stopping next time"
                            )
            
            # Indicator 2: Epochs vs dataset size ratio
            if lora_model.training_steps and lora_model.dataset_id:
                from app.models.training_dataset import TrainingDataset
                from app.config.database import async_session_factory
                from sqlalchemy import select
                
                async with async_session_factory() as session:
                    dataset = await session.get(TrainingDataset, lora_model.dataset_id)
                    if dataset and dataset.image_count:
                        # Rule of thumb: 100-200 steps per image is reasonable
                        steps_per_image = lora_model.training_steps / dataset.image_count
                        
                        if steps_per_image > 300:
                            if not result["is_overfitting"]:
                                result["is_overfitting"] = True
                                result["severity"] = "moderate"
                                result["confidence"] = 0.6
                            result["indicators"].append(
                                f"High training ratio: {steps_per_image:.0f} steps/image "
                                f"(recommended: 100-200)"
                            )
                            result["recommendations"].append(
                                f"Reduce training steps or add more images "
                                f"(current: {dataset.image_count} images)"
                            )
            
            # Indicator 3: Very low final loss with poor quality
            if lora_model.final_loss is not None and lora_model.final_loss < 0.005:
                result["indicators"].append(
                    f"Very low final loss ({lora_model.final_loss:.5f}) may indicate memorization"
                )
                if not result["is_overfitting"]:
                    result["is_overfitting"] = True
                    result["severity"] = "mild"
                    result["confidence"] = 0.4
                result["recommendations"].append(
                    "Very low loss can mean memorization. Check generated images for diversity"
                )
            
            logger.info(
                f"Overfitting detection for LoRA {lora_model.id}: "
                f"overfitting={result['is_overfitting']}, severity={result['severity']}"
            )
            
        except Exception as e:
            logger.error(f"Failed to detect overfitting: {e}")
            result["error"] = str(e)
        
        return result
    
    async def detect_underfitting(self, lora_model: LoRAModel) -> Dict[str, Any]:
        """
        Detect underfitting in trained LoRA model.
        
        Analyzes:
        - Loss convergence (loss barely decreases)
        - Training completion (too few epochs/steps)
        - Quality score correlation
        
        Args:
            lora_model: Trained LoRA model
            
        Returns:
            Detection result with severity and recommendations
        """
        result = {
            "is_underfitting": False,
            "severity": "none",  # none, mild, moderate, severe
            "confidence": 0.0,
            "indicators": [],
            "recommendations": []
        }
        
        try:
            # Get training metrics
            from app.services.training_logger import training_logger
            metrics = await training_logger.get_metrics(lora_model.id)
            losses = metrics.get("losses", [])
            
            # Indicator 1: Loss barely decreases
            if len(losses) >= 5:
                initial_loss = losses[0]
                final_loss = losses[-1]
                
                if initial_loss > 0:
                    loss_reduction_ratio = (initial_loss - final_loss) / initial_loss
                    
                    if loss_reduction_ratio < 0.3:  # Less than 30% reduction
                        result["is_underfitting"] = True
                        result["severity"] = "severe"
                        result["confidence"] = 0.8
                        result["indicators"].append(
                            f"Loss only reduced by {loss_reduction_ratio*100:.1f}% "
                            f"(from {initial_loss:.4f} to {final_loss:.4f})"
                        )
                        result["recommendations"].append(
                            "Increase training epochs significantly (2-3x current)"
                        )
                    elif loss_reduction_ratio < 0.5:  # Less than 50% reduction
                        result["is_underfitting"] = True
                        result["severity"] = "moderate"
                        result["confidence"] = 0.6
                        result["indicators"].append(
                            f"Limited loss reduction: {loss_reduction_ratio*100:.1f}%"
                        )
                        result["recommendations"].append(
                            "Increase training epochs by 50-100%"
                        )
            
            # Indicator 2: Too few training steps
            if lora_model.training_steps:
                if lora_model.training_steps < 500:
                    if not result["is_underfitting"]:
                        result["is_underfitting"] = True
                        result["severity"] = "moderate"
                        result["confidence"] = 0.7
                    result["indicators"].append(
                        f"Very few training steps: {lora_model.training_steps} "
                        f"(recommended: 1000+)"
                    )
                    result["recommendations"].append(
                        "Train for at least 1000-2000 steps for acceptable quality"
                    )
                elif lora_model.training_steps < 1000:
                    result["indicators"].append(
                        f"Low training steps: {lora_model.training_steps}"
                    )
                    if not result["is_underfitting"]:
                        result["is_underfitting"] = True
                        result["severity"] = "mild"
                        result["confidence"] = 0.5
                    result["recommendations"].append(
                        "Consider training for 1000+ steps"
                    )
            
            # Indicator 3: High final loss
            if lora_model.final_loss is not None and lora_model.final_loss > 0.15:
                result["indicators"].append(
                    f"High final loss: {lora_model.final_loss:.4f}"
                )
                if not result["is_underfitting"]:
                    result["is_underfitting"] = True
                    result["severity"] = "moderate"
                    result["confidence"] = 0.6
                result["recommendations"].append(
                    "High loss indicates incomplete training. Increase epochs or check dataset quality"
                )
            
            logger.info(
                f"Underfitting detection for LoRA {lora_model.id}: "
                f"underfitting={result['is_underfitting']}, severity={result['severity']}"
            )
            
        except Exception as e:
            logger.error(f"Failed to detect underfitting: {e}")
            result["error"] = str(e)
        
        return result
    
    async def generate_training_diagnosis(self, lora_model: LoRAModel) -> Dict[str, Any]:
        """
        Generate comprehensive training diagnosis.
        
        Combines overfitting and underfitting detection
        with actionable recommendations.
        
        Args:
            lora_model: Trained LoRA model
            
        Returns:
            Complete diagnosis report
        """
        overfitting = await self.detect_overfitting(lora_model)
        underfitting = await self.detect_underfitting(lora_model)
        
        # Determine overall status
        if overfitting["is_overfitting"] and underfitting["is_underfitting"]:
            # Both detected - usually means inconsistent training
            overall_status = "inconsistent"
            primary_issue = "overfitting" if overfitting["confidence"] > underfitting["confidence"] else "underfitting"
        elif overfitting["is_overfitting"]:
            overall_status = "overfitting"
            primary_issue = "overfitting"
        elif underfitting["is_underfitting"]:
            overall_status = "underfitting"
            primary_issue = "underfitting"
        else:
            overall_status = "healthy"
            primary_issue = "none"
        
        # Combine recommendations
        all_recommendations = []
        if overfitting["recommendations"]:
            all_recommendations.extend(overfitting["recommendations"])
        if underfitting["recommendations"]:
            all_recommendations.extend(underfitting["recommendations"])
        
        if overall_status == "healthy" and lora_model.final_loss is not None:
            if lora_model.final_loss < 0.05:
                all_recommendations.append("Training looks good! Model is ready to use.")
            else:
                all_recommendations.append("Model is acceptable but could benefit from more training.")
        
        return {
            "overall_status": overall_status,
            "primary_issue": primary_issue,
            "overfitting": overfitting,
            "underfitting": underfitting,
            "recommendations": all_recommendations,
            "can_use_model": overall_status == "healthy" or (
                overall_status in ["overfitting", "underfitting"] and 
                overfitting.get("severity") in ["none", "mild"] and
                underfitting.get("severity") in ["none", "mild"]
            ),
        }
    
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
    
    async def _calculate_clip_consistency(
        self,
        lora_model: LoRAModel,
        test_images: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate CLIP-based character consistency score.
        
        Compares generated test images with IP reference images.
        
        Args:
            lora_model: Trained LoRA model
            test_images: Generated test images
            
        Returns:
            Consistency score (0-100)
        """
        # Check if CLIP is available
        if not self.clip_calculator.is_available():
            logger.warning("CLIP not available, using default consistency score")
            return 60.0  # Default moderate score
        
        try:
            # Get IP asset reference images
            reference_images = await self._get_reference_images(lora_model)
            
            if not reference_images:
                logger.warning("No reference images found, using default score")
                return 60.0
            
            # Get test image paths
            test_paths = [
                img["image_path"] for img in test_images
                if img.get("image_path") and Path(img["image_path"]).exists()
            ]
            
            if not test_paths:
                logger.warning("No valid test images")
                return 50.0
            
            # Calculate consistency
            consistency = self.clip_calculator.assess_character_consistency(
                reference_images=reference_images,
                test_images=test_paths,
            )
            
            # Convert to 0-100 scale
            score = consistency["consistency_score"] * 100.0
            
            logger.info(f"CLIP consistency score: {score:.2f}/100")
            
            return score
        
        except Exception as e:
            logger.error(f"Failed to calculate CLIP consistency: {e}")
            return 60.0  # Default on error
    
    async def _get_reference_images(self, lora_model: LoRAModel) -> List[str]:
        """
        Get reference images from IP asset.
        
        Args:
            lora_model: LoRA model
            
        Returns:
            List of reference image paths
        """
        try:
            from app.models.ip_asset import IPAsset
            from app.config.database import async_session_factory
            from sqlalchemy import select
            
            async with async_session_factory() as session:
                # Get associated IP asset
                if not lora_model.ip_asset_id:
                    return []
                
                ip_asset = await session.get(IPAsset, lora_model.ip_asset_id)
                if not ip_asset:
                    return []
                
                # Get reference images
                reference_paths = []
                
                # Main reference images
                if ip_asset.reference_images:
                    for img_info in ip_asset.reference_images:
                        if isinstance(img_info, dict) and "path" in img_info:
                            path = Path(img_info["path"])
                            if path.exists():
                                reference_paths.append(str(path))
                
                # Multi-view images
                if hasattr(ip_asset, 'multi_views') and ip_asset.multi_views:
                    for view in ip_asset.multi_views:
                        if view.get("image_path"):
                            path = Path(view["image_path"])
                            if path.exists():
                                reference_paths.append(str(path))
                
                return reference_paths[:10]  # Limit to 10 reference images
        
        except Exception as e:
            logger.error(f"Failed to get reference images: {e}")
            return []
    
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
            
            # Generate training diagnosis (overfitting/underfitting detection)
            diagnosis = await self.generate_training_diagnosis(lora_model)
            
            # Combine recommendations
            base_recommendations = self._generate_recommendations(quality_scores, lora_model)
            all_recommendations = base_recommendations + diagnosis["recommendations"]
            
            # Create quality report
            report = QualityReport(
                lora_id=lora_id,
                overall_score=quality_scores["overall_score"],
                grade=quality_scores["grade"],
                loss_score=quality_scores["loss_score"],
                completion_score=quality_scores["completion_score"],
                file_score=quality_scores["file_score"],
                generation_success=quality_scores["generation_success"],
                clip_consistency=quality_scores.get("clip_consistency", 0),
                test_images=test_images,
                recommendations=all_recommendations,
                training_diagnosis=diagnosis,
                status="completed",
            )
            
            session.add(report)
            await session.commit()
            await session.refresh(report)
            
            logger.info(
                f"Quality report created for LoRA {lora_id}: "
                f"{quality_scores['overall_score']}/100 ({quality_scores['grade']}), "
                f"diagnosis={diagnosis['overall_status']}"
            )
            
            return report
    
    def _generate_recommendations(
        self,
        quality_scores: Dict[str, Any],
        lora_model: LoRAModel,
    ) -> List[Dict[str, str]]:
        """Generate optimization recommendations based on quality scores."""
        recommendations = []
        
        # Loss-based recommendations
        if quality_scores["loss_score"] < 70:
            recommendations.append({
                "text": (
                    "High training loss detected. Consider increasing training epochs "
                    "or adjusting learning rate for better convergence."
                ),
                "type": "warning"
            })
        
        # Completion-based recommendations
        if quality_scores["completion_score"] < 70:
            if lora_model.training_steps and lora_model.training_steps < 1000:
                recommendations.append({
                    "text": (
                        f"Low training steps ({lora_model.training_steps}). "
                        "Consider training for at least 1000 steps for better quality."
                    ),
                    "type": "warning"
                })
        
        # File-based recommendations
        if quality_scores["file_score"] < 60:
            recommendations.append({
                "text": (
                    "Model file size is smaller than expected. "
                    "This may indicate incomplete training or configuration issues."
                ),
                "type": "error"
            })
        
        # Generation success recommendations
        if quality_scores["generation_success"] < 80:
            recommendations.append({
                "text": (
                    "Some test images failed to generate. "
                    "Check model file integrity and configuration."
                ),
                "type": "error"
            })
        
        # Overall recommendations
        overall = quality_scores["overall_score"]
        if overall < 60:
            recommendations.append({
                "text": (
                    "Overall quality is low. Consider retraining with different parameters: "
                    "increase epochs, adjust learning rate, or use more training data."
                ),
                "type": "error"
            })
        elif overall >= 80:
            recommendations.append({
                "text": (
                    "Model quality is good! You can start using this LoRA for generation. "
                    "Consider fine-tuning parameters for even better results."
                ),
                "type": "success"
            })
        
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
