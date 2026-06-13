"""
Caption Generator for LoRA Training

Generates caption files for training images based on annotations and features.
Uses fixed template system to ensure consistency and quality.
"""
from typing import Dict, Optional
from app.config.feature_types import FEATURE_TYPE_CONFIG


# Fixed caption template
# Format: {trigger_word}, {angle} view, {pose}, {outfit}, {expression}, ...
CAPTION_TEMPLATE = "{trigger_word}, {angle} view{, extras}"


def generate_caption_from_annotation(
    trigger_word: str,
    angle: str,
    pose: Optional[str] = None,
    background: Optional[str] = None,
    features: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate caption from image annotation and features.
    
    Args:
        trigger_word: IP trigger word (e.g., "xiao_huli_character")
        angle: View angle (front/side/back)
        pose: Pose type (standing/sitting/running/jumping)
        background: Background type (white/indoor/outdoor/nature)
        features: Dict of feature_type -> feature_name
                  Example: {"outfit": "casual_wear", "expression": "happy"}
    
    Returns:
        str: Generated caption
    
    Example:
        >>> generate_caption_from_annotation(
        ...     trigger_word="xiao_huli_character",
        ...     angle="front",
        ...     pose="standing",
        ...     background="white",
        ...     features={"outfit": "casual_wear", "expression": "happy"}
        ... )
        "xiao_huli_character, front view, standing pose, wearing casual_wear, happy expression, white background"
    """
    parts = [trigger_word]
    
    # Add angle view
    angle_map = {
        "front": "front view",
        "side": "side view",
        "back": "back view"
    }
    angle_text = angle_map.get(angle, f"{angle} view")
    parts.append(angle_text)
    
    # Add features based on caption_position (sorted)
    if features:
        # Sort features by their caption_position
        sorted_features = []
        for feature_type, feature_name in features.items():
            config = FEATURE_TYPE_CONFIG.get(feature_type)
            if config:
                position = config.get("caption_position", 99)
                trigger_phrase = config["trigger_template"].format(feature_name=feature_name)
                sorted_features.append((position, trigger_phrase))
        
        # Sort by position and add to parts
        sorted_features.sort(key=lambda x: x[0])
        for _, trigger_phrase in sorted_features:
            parts.append(trigger_phrase)
    
    # Add pose if provided
    if pose:
        # Check if pose is already in features
        if not features or "pose" not in features:
            parts.append(f"{pose} pose")
    
    # Add background if provided
    if background:
        bg_map = {
            "white": "white background",
            "indoor": "indoor",
            "outdoor": "outdoor",
            "nature": "nature background"
        }
        bg_text = bg_map.get(background, background)
        parts.append(bg_text)
    
    # Join all parts
    caption = ", ".join([p for p in parts if p])
    return caption


def generate_caption_batch(
    trigger_word: str,
    annotations: list
) -> list:
    """
    Generate captions for a batch of images.
    
    Args:
        trigger_word: IP trigger word
        annotations: List of annotation dicts
                    Each dict should have: angle, pose, background, features
    
    Returns:
        list: List of generated captions
    
    Example:
        >>> annotations = [
        ...     {"angle": "front", "pose": "standing", "background": "white", 
        ...      "features": {"outfit": "casual_wear"}},
        ...     {"angle": "side", "pose": "sitting", "background": "indoor",
        ...      "features": {"outfit": "kimono", "expression": "happy"}}
        ... ]
        >>> generate_caption_batch("xiao_huli", annotations)
        [
            "xiao_huli, front view, standing pose, wearing casual_wear, white background",
            "xiao_huli, side view, sitting pose, wearing kimono, happy expression, indoor"
        ]
    """
    captions = []
    for annotation in annotations:
        caption = generate_caption_from_annotation(
            trigger_word=trigger_word,
            angle=annotation.get("angle", "front"),
            pose=annotation.get("pose"),
            background=annotation.get("background"),
            features=annotation.get("features", {})
        )
        captions.append(caption)
    
    return captions
