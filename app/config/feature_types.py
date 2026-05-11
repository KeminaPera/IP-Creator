"""
Feature Type Configuration

Defines all supported feature types for IP character features.
This configuration system enables dynamic extension without code changes.

To add a new feature type:
1. Add a new entry in FEATURE_TYPE_CONFIG
2. Frontend will automatically display it
3. No database schema changes needed
"""

FEATURE_TYPE_CONFIG = {
    "outfit": {
        "type": "outfit",
        "display_name": "服装",
        "display_name_en": "Outfit",
        "icon": "👗",
        "trigger_template": "wearing {feature_name}",
        "required": True,
        "min_images": 3,  # front/side/back
        "caption_position": 3,
        "description": "角色的服装变体（常服、和服、机甲风格等）",
        "description_en": "Character outfit variations (casual, kimono, mecha, etc.)"
    },
    "expression": {
        "type": "expression",
        "display_name": "表情",
        "display_name_en": "Expression",
        "icon": "😊",
        "trigger_template": "{feature_name} expression",
        "required": True,
        "min_images": 1,  # front only
        "caption_position": 4,
        "description": "角色的表情变化（开心、生气、惊讶等）",
        "description_en": "Character expression variations (happy, angry, surprised, etc.)"
    },
    "pose": {
        "type": "pose",
        "display_name": "动作",
        "display_name_en": "Pose",
        "icon": "🏃",
        "trigger_template": "{feature_name} pose",
        "required": True,
        "min_images": 3,  # front/side/back
        "caption_position": 2,
        "description": "角色的动作姿态（站立、坐着、跑步等）",
        "description_en": "Character pose variations (standing, sitting, running, etc.)"
    },
    # Future extensible feature types (commented for reference):
    # "accessory": {
    #     "type": "accessory",
    #     "display_name": "配饰",
    #     "display_name_en": "Accessory",
    #     "icon": "👓",
    #     "trigger_template": "wearing {feature_name}",
    #     "required": False,
    #     "min_images": 1,
    #     "caption_position": 5,
    #     "description": "角色的配饰（眼镜、帽子、首饰等）",
    #     "description_en": "Character accessories (glasses, hats, jewelry, etc.)"
    # },
    # "background": {
    #     "type": "background",
    #     "display_name": "背景",
    #     "display_name_en": "Background",
    #     "icon": "🏞️",
    #     "trigger_template": "in {feature_name}",
    #     "required": False,
    #     "min_images": 1,
    #     "caption_position": 6,
    #     "description": "背景场景（森林、城市、室内等）",
    #     "description_en": "Background scenes (forest, city, indoor, etc.)"
    # },
    # "hairstyle": {
    #     "type": "hairstyle",
    #     "display_name": "发型",
    #     "display_name_en": "Hairstyle",
    #     "icon": "💇",
    #     "trigger_template": "with {feature_name}",
    #     "required": False,
    #     "min_images": 3,
    #     "caption_position": 5,
    #     "description": "角色的发型（长发、短发、辫子等）",
    #     "description_en": "Character hairstyles (long hair, short hair, ponytail, etc.)"
    # },
}


def get_feature_types():
    """
    Get all supported feature types.
    
    Returns:
        list: List of feature type configurations
    """
    return list(FEATURE_TYPE_CONFIG.values())


def get_feature_type(feature_type: str):
    """
    Get configuration for a specific feature type.
    
    Args:
        feature_type: Feature type name (e.g., "outfit", "expression")
    
    Returns:
        dict: Feature type configuration, or None if not found
    """
    return FEATURE_TYPE_CONFIG.get(feature_type)


def is_feature_type_valid(feature_type: str) -> bool:
    """
    Check if a feature type is valid.
    
    Args:
        feature_type: Feature type name
    
    Returns:
        bool: True if valid, False otherwise
    """
    return feature_type in FEATURE_TYPE_CONFIG


def get_trigger_phrase(feature_type: str, feature_name: str) -> str:
    """
    Generate trigger phrase for a feature.
    
    Args:
        feature_type: Feature type name
        feature_name: Feature name (e.g., "casual_wear", "happy")
    
    Returns:
        str: Generated trigger phrase
    
    Example:
        >>> get_trigger_phrase("outfit", "casual_wear")
        "wearing casual_wear"
    """
    config = FEATURE_TYPE_CONFIG.get(feature_type)
    if not config:
        return feature_name
    
    template = config.get("trigger_template", "{feature_name}")
    return template.format(feature_name=feature_name)
