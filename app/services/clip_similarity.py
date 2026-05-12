"""
CLIP Similarity Calculation Service

Calculates similarity between images using CLIP embeddings.
Used for quality assessment of LoRA-generated images.
"""
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from app.utils.logger import logger


class CLIPSimilarityCalculator:
    """
    Service for calculating image similarity using CLIP model.
    
    Features:
    - Image-to-image similarity
    - Image-to-text similarity
    - Batch processing
    - Multiple CLIP model support
    """
    
    def __init__(self, model_name: str = "ViT-B/32"):
        """
        Initialize CLIP similarity calculator.
        
        Args:
            model_name: CLIP model name (ViT-B/32, ViT-B/16, ViT-L/14)
        """
        self.model_name = model_name
        self.model = None
        self.preprocess = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Try to load CLIP model
        self._load_model()
    
    def _load_model(self):
        """Load CLIP model."""
        try:
            import clip
            
            self.model, self.preprocess = clip.load(self.model_name, device=self.device)
            self.model.eval()
            
            logger.info(f"CLIP model loaded: {self.model_name} on {self.device}")
        
        except ImportError:
            logger.warning("CLIP not installed. Install with: pip install git+https://github.com/openai/CLIP.git")
            self.model = None
            self.preprocess = None
        
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            self.model = None
            self.preprocess = None
    
    def is_available(self) -> bool:
        """Check if CLIP model is available."""
        return self.model is not None and self.preprocess is not None
    
    def encode_image(self, image_path: str) -> Optional[torch.Tensor]:
        """
        Encode a single image to CLIP embedding.
        
        Args:
            image_path: Path to image file
            
        Returns:
            CLIP embedding vector
        """
        if not self.is_available():
            logger.warning("CLIP not available")
            return None
        
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Encode image
            with torch.no_grad():
                embedding = self.model.encode_image(image_tensor)
            
            # Normalize embedding
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)
            
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            return None
    
    def encode_text(self, text: str) -> Optional[torch.Tensor]:
        """
        Encode text to CLIP embedding.
        
        Args:
            text: Text to encode
            
        Returns:
            CLIP embedding vector
        """
        if not self.is_available():
            logger.warning("CLIP not available")
            return None
        
        try:
            import clip
            
            # Tokenize text
            text_tokens = clip.tokenize([text]).to(self.device)
            
            # Encode text
            with torch.no_grad():
                embedding = self.model.encode_text(text_tokens)
            
            # Normalize embedding
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)
            
            return embedding
        
        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            return None
    
    def calculate_image_similarity(
        self,
        image1_path: str,
        image2_path: str,
    ) -> float:
        """
        Calculate similarity between two images.
        
        Args:
            image1_path: Path to first image
            image2_path: Path to second image
            
        Returns:
            Similarity score (0.0 - 1.0)
        """
        if not self.is_available():
            logger.warning("CLIP not available, returning default similarity")
            return 0.5  # Default neutral score
        
        try:
            # Encode both images
            embedding1 = self.encode_image(image1_path)
            embedding2 = self.encode_image(image2_path)
            
            if embedding1 is None or embedding2 is None:
                return 0.5
            
            # Calculate cosine similarity
            similarity = (embedding1 @ embedding2.T).item()
            
            # Clamp to [0, 1]
            similarity = max(0.0, min(1.0, similarity))
            
            return similarity
        
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.5
    
    def calculate_batch_similarity(
        self,
        reference_path: str,
        test_paths: List[str],
    ) -> List[float]:
        """
        Calculate similarity between reference image and multiple test images.
        
        Args:
            reference_path: Path to reference image
            test_paths: List of test image paths
            
        Returns:
            List of similarity scores
        """
        if not self.is_available():
            return [0.5] * len(test_paths)
        
        # Encode reference image
        reference_embedding = self.encode_image(reference_path)
        if reference_embedding is None:
            return [0.5] * len(test_paths)
        
        similarities = []
        
        for test_path in test_paths:
            try:
                test_embedding = self.encode_image(test_path)
                if test_embedding is None:
                    similarities.append(0.5)
                    continue
                
                # Calculate similarity
                similarity = (reference_embedding @ test_embedding.T).item()
                similarity = max(0.0, min(1.0, similarity))
                similarities.append(similarity)
            
            except Exception as e:
                logger.error(f"Failed to process {test_path}: {e}")
                similarities.append(0.5)
        
        return similarities
    
    def calculate_text_image_similarity(
        self,
        text: str,
        image_path: str,
    ) -> float:
        """
        Calculate similarity between text and image.
        
        Args:
            text: Text description
            image_path: Path to image
            
        Returns:
            Similarity score (0.0 - 1.0)
        """
        if not self.is_available():
            return 0.5
        
        try:
            # Encode text and image
            text_embedding = self.encode_text(text)
            image_embedding = self.encode_image(image_path)
            
            if text_embedding is None or image_embedding is None:
                return 0.5
            
            # Calculate similarity
            similarity = (text_embedding @ image_embedding.T).item()
            similarity = max(0.0, min(1.0, similarity))
            
            return similarity
        
        except Exception as e:
            logger.error(f"Failed to calculate text-image similarity: {e}")
            return 0.5
    
    def assess_character_consistency(
        self,
        reference_images: List[str],
        test_images: List[str],
    ) -> Dict[str, Any]:
        """
        Assess character consistency between reference and test images.
        
        Args:
            reference_images: List of reference image paths (IP character)
            test_images: List of test image paths (generated by LoRA)
            
        Returns:
            Consistency assessment results
        """
        if not self.is_available():
            return {
                "consistency_score": 0.5,
                "details": "CLIP not available",
            }
        
        if not reference_images or not test_images:
            return {
                "consistency_score": 0.0,
                "details": "No images provided",
            }
        
        similarities = []
        details = []
        
        # Compare each test image with each reference image
        for i, test_path in enumerate(test_images):
            test_similarities = []
            
            for j, ref_path in enumerate(reference_images):
                try:
                    similarity = self.calculate_image_similarity(ref_path, test_path)
                    test_similarities.append(similarity)
                    
                    details.append({
                        "test_image": i + 1,
                        "reference_image": j + 1,
                        "similarity": round(similarity, 4),
                    })
                
                except Exception as e:
                    logger.error(f"Failed to compare images: {e}")
                    test_similarities.append(0.5)
            
            # Average similarity for this test image
            avg_similarity = np.mean(test_similarities)
            similarities.append(avg_similarity)
        
        # Overall consistency score
        overall_score = np.mean(similarities) if similarities else 0.0
        
        # Statistics
        stats = {
            "consistency_score": round(float(overall_score), 4),
            "min_similarity": round(float(np.min(similarities)), 4) if similarities else 0.0,
            "max_similarity": round(float(np.max(similarities)), 4) if similarities else 0.0,
            "avg_similarity": round(float(overall_score), 4),
            "std_similarity": round(float(np.std(similarities)), 4) if similarities else 0.0,
            "test_images_count": len(test_images),
            "reference_images_count": len(reference_images),
            "details": details,
        }
        
        return stats
    
    def assess_prompt_alignment(
        self,
        prompts: List[str],
        test_images: List[str],
    ) -> Dict[str, Any]:
        """
        Assess how well generated images match their prompts.
        
        Args:
            prompts: List of text prompts
            test_images: List of generated image paths
            
        Returns:
            Prompt alignment assessment results
        """
        if not self.is_available():
            return {
                "alignment_score": 0.5,
                "details": "CLIP not available",
            }
        
        if len(prompts) != len(test_images):
            logger.warning(f"Prompts ({len(prompts)}) and images ({len(test_images)}) count mismatch")
            return {
                "alignment_score": 0.0,
                "details": "Count mismatch",
            }
        
        similarities = []
        details = []
        
        for i, (prompt, image_path) in enumerate(zip(prompts, test_images)):
            try:
                similarity = self.calculate_text_image_similarity(prompt, image_path)
                similarities.append(similarity)
                
                details.append({
                    "image_index": i + 1,
                    "prompt": prompt[:100],
                    "similarity": round(similarity, 4),
                })
            
            except Exception as e:
                logger.error(f"Failed to assess prompt alignment: {e}")
                similarities.append(0.5)
        
        overall_score = np.mean(similarities) if similarities else 0.0
        
        return {
            "alignment_score": round(float(overall_score), 4),
            "min_alignment": round(float(np.min(similarities)), 4) if similarities else 0.0,
            "max_alignment": round(float(np.max(similarities)), 4) if similarities else 0.0,
            "avg_alignment": round(float(overall_score), 4),
            "details": details,
        }
