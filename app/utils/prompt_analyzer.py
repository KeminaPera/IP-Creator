"""
Prompt Analyzer

Analyzes generation prompts to extract target attributes for intelligent
reference image selection and adaptive IP-Adapter scale calculation.

Uses keyword-based pattern matching (no LLM required) for fast, reliable analysis.
"""
import re
from typing import Dict, List, Optional, Tuple
from app.utils.logger import logger


class PromptAnalyzer:
    """
    Analyze prompts to extract generation attributes.
    
    Extracts:
    - Camera angle (front, side, back, closeup, full_body)
    - Expression (neutral, happy, sad, surprised, angry)
    - Pose (standing, sitting, running, dynamic)
    - Scene context (character-focused, scene-focused, action)
    """
    
    # Keyword patterns for angle detection
    ANGLE_PATTERNS = {
        'front': [r'\bfront view\b', r'\bfront\b', r'\bfrontal\b', r'\blooking at camera\b', r'\bportrait\b'],
        'side': [r'\bside view\b', r'\bside\b', r'\bprofile\b', r'\bsideways\b', r'\bfrom the side\b'],
        'back': [r'\bback view\b', r'\bback\b', r'\bfrom behind\b', r'\bbackside\b', r'\bposterior\b'],
        'closeup': [r'\bcloseup\b', r'\bclose-up\b', r'\bclose up\b', r'\bface\b', r'\bheadshot\b', r'\bportrait\b'],
        'full_body': [r'\bfull body\b', r'\bfull-body\b', r'\bentire body\b', r'\bhead to toe\b', r'\bwalking\b'],
        'top': [r'\btop view\b', r'\bfrom above\b', r'\bbird\s*eye\b', r'\baerial\b'],
        'low': [r'\blow angle\b', r'\bfrom below\b', r'\blooking up\b'],
    }
    
    # Keyword patterns for expression detection
    EXPRESSION_PATTERNS = {
        'neutral': [r'\bneutral\b', r'\bcalm\b', r'\brelaxed\b', r'\bpeaceful\b', r'\bserious\b'],
        'happy': [r'\bhappy\b', r'\bsmile\b', r'\bsmiling\b', r'\bgrin\b', r'\bjoy\b', r'\bcheerful\b', r'\bjoyful\b'],
        'sad': [r'\bsad\b', r'\bsadness\b', r'\bmelancholy\b', r'\bsorrow\b', r'\btear\b', r'\bcrying\b', r'\bunhappy\b'],
        'surprised': [r'\bsurprised\b', r'\bsurprise\b', r'\bamazed\b', r'\bshocked\b', r'\bwow\b', r'\bastonished\b'],
        'angry': [r'\bangry\b', r'\bfurious\b', r'\brage\b', r'\bmad\b', r'\bannoyed\b', r'\bfrustrated\b'],
        'excited': [r'\bexcited\b', r'\bexcitement\b', r'\bthrilled\b', r'\beager\b', r'\benthusiastic\b'],
        'sleepy': [r'\bsleepy\b', r'\bsleeping\b', r'\btired\b', r'\bexhausted\b', r'\bdrowsy\b', r'\byawn\b'],
        'determined': [r'\bdetermined\b', r'\bdetermination\b', r'\bfocused\b', r'\bconfident\b', r'\bbrave\b'],
    }
    
    # Keyword patterns for pose detection
    POSE_PATTERNS = {
        'standing': [r'\bstanding\b', r'\bstand\b', r'\bupright\b'],
        'sitting': [r'\bsitting\b', r'\bsit\b', r'\bseated\b', r'\bon a chair\b'],
        'running': [r'\brunning\b', r'\brun\b', r'\bsprinting\b', r'\bjogging\b', r'\bdashing\b'],
        'jumping': [r'\bjumping\b', r'\bjump\b', r'\bleaping\b', r'\bhopping\b'],
        'dynamic': [r'\bdynamic pose\b', r'\baction pose\b', r'\bfighting\b', r'\bbattle\b', r'\bcombat\b'],
        'walking': [r'\bwalking\b', r'\bwalk\b', r'\bstrolling\b', r'\bwandering\b'],
        'dancing': [r'\bdancing\b', r'\bdance\b', r'\bballet\b'],
        'flying': [r'\bflying\b', r'\bfly\b', r'\bsoaring\b', r'\bhovering\b'],
        'lying': [r'\blying\b', r'\blaying\b', r'\bresting\b', r'\bsleeping\b'],
    }
    
    # Keyword patterns for scene context
    SCENE_PATTERNS = {
        'character': [r'\bcharacter\b', r'\bportrait\b', r'\bface\b', r'\bbody\b', r'\bperson\b'],
        'scene': [r'\bscene\b', r'\blandscape\b', r'\benvironment\b', r'\bbackground\b', r'\bsetting\b'],
        'action': [r'\baction\b', r'\bbattle\b', r'\bfight\b', r'\badventure\b', r'\bchase\b'],
        'indoor': [r'\bindoor\b', r'\binside\b', r'\broom\b', r'\bhouse\b', r'\bstudio\b', r'\bbedroom\b'],
        'outdoor': [r'\boutdoor\b', r'\boutside\b', r'\bnature\b', r'\bforest\b', r'\bgarden\b', r'\bpark\b'],
    }
    
    @classmethod
    def analyze_prompt(cls, prompt: str) -> Dict[str, str]:
        """
        Analyze prompt to extract target attributes.
        
        Args:
            prompt: Generation prompt text
            
        Returns:
            Dictionary with extracted attributes:
            {
                "angle": "front" | "side" | "back" | "closeup" | "full_body" | "unknown",
                "expression": "neutral" | "happy" | "sad" | ... | "unknown",
                "pose": "standing" | "sitting" | "running" | ... | "unknown",
                "scene_context": "character" | "scene" | "action" | "mixed",
                "environment": "indoor" | "outdoor" | "unknown"
            }
        """
        if not prompt:
            logger.warning("Empty prompt provided for analysis")
            return {
                "angle": "unknown",
                "expression": "unknown",
                "pose": "unknown",
                "scene_context": "unknown",
                "environment": "unknown"
            }
        
        prompt_lower = prompt.lower()
        
        result = {
            "angle": cls._detect_attribute(prompt_lower, cls.ANGLE_PATTERNS, "angle"),
            "expression": cls._detect_attribute(prompt_lower, cls.EXPRESSION_PATTERNS, "expression"),
            "pose": cls._detect_attribute(prompt_lower, cls.POSE_PATTERNS, "pose"),
            "scene_context": cls._detect_scene_context(prompt_lower),
            "environment": cls._detect_environment(prompt_lower),
        }
        
        logger.debug(f"Prompt analysis result: {result}")
        return result
    
    @classmethod
    def _detect_attribute(
        cls, 
        prompt_lower: str, 
        patterns: Dict[str, List[str]], 
        attribute_name: str
    ) -> str:
        """
        Detect attribute by matching patterns.
        
        Args:
            prompt_lower: Lowercase prompt text
            patterns: Dictionary of attribute -> pattern list
            attribute_name: Name for logging
            
        Returns:
            Matched attribute value or "unknown"
        """
        matches = []
        
        for value, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, prompt_lower):
                    matches.append((value, pattern))
                    break  # One match per value is enough
        
        if not matches:
            return "unknown"
        
        # Return the first match (could implement scoring if needed)
        matched_value = matches[0][0]
        logger.debug(f"Detected {attribute_name}: {matched_value} (patterns: {len(matches)})")
        return matched_value
    
    @classmethod
    def _detect_scene_context(cls, prompt_lower: str) -> str:
        """
        Detect overall scene context.
        
        Returns:
            "character", "scene", "action", or "mixed"
        """
        contexts = set()
        
        for context, pattern_list in cls.SCENE_PATTERNS.items():
            for pattern in pattern_list:
                if re.search(pattern, prompt_lower):
                    contexts.add(context)
                    break
        
        if not contexts:
            return "unknown"
        
        # Character + action = mixed
        if len(contexts) > 1:
            return "mixed"
        
        return list(contexts)[0]
    
    @classmethod
    def _detect_environment(cls, prompt_lower: str) -> str:
        """
        Detect environment setting.
        
        Returns:
            "indoor", "outdoor", or "unknown"
        """
        indoor_count = 0
        outdoor_count = 0
        
        # Check indoor patterns
        for pattern in ['indoor', 'inside', 'room', 'house', 'studio', 'bedroom', 'kitchen', 'office']:
            if re.search(r'\b' + pattern + r'\b', prompt_lower):
                indoor_count += 1
        
        # Check outdoor patterns
        for pattern in ['outdoor', 'outside', 'nature', 'forest', 'garden', 'park', 'street', 'beach', 'mountain']:
            if re.search(r'\b' + pattern + r'\b', prompt_lower):
                outdoor_count += 1
        
        if indoor_count > outdoor_count:
            return "indoor"
        elif outdoor_count > indoor_count:
            return "outdoor"
        else:
            return "unknown"
    
    @classmethod
    def calculate_similarity_score(
        cls,
        prompt_attributes: Dict[str, str],
        image_attributes: Dict[str, str],
    ) -> float:
        """
        Calculate similarity score between prompt and image attributes.
        
        Args:
            prompt_attributes: Attributes extracted from prompt
            image_attributes: Attributes of reference image
            
        Returns:
            Similarity score (0.0-1.0)
        """
        scores = []
        weights = {
            "angle": 0.40,      # Angle is most important
            "expression": 0.30,  # Expression is important
            "pose": 0.30,        # Pose is important
        }
        
        for attribute, weight in weights.items():
            prompt_val = prompt_attributes.get(attribute, "unknown")
            image_val = image_attributes.get(attribute, "unknown")
            
            # Exact match
            if prompt_val == image_val and prompt_val != "unknown":
                scores.append(weight)
            # Partial match (both unknown or similar)
            elif prompt_val == "unknown" or image_val == "unknown":
                scores.append(weight * 0.5)  # Neutral score
            # No match
            else:
                scores.append(0.0)
        
        return sum(scores)
    
    @classmethod
    def extract_key_phrases(cls, prompt: str) -> List[str]:
        """
        Extract key descriptive phrases from prompt.
        
        Useful for understanding generation intent.
        
        Args:
            prompt: Full prompt text
            
        Returns:
            List of key phrases
        """
        phrases = []
        
        # Remove common filler words
        cleaned = re.sub(r'\b(a|an|the|with|in|on|at|by|for|of|to)\b', '', prompt.lower())
        
        # Extract comma-separated phrases
        parts = [p.strip() for p in cleaned.split(',') if p.strip()]
        phrases.extend(parts)
        
        return phrases


# Global analyzer instance
prompt_analyzer = PromptAnalyzer()
