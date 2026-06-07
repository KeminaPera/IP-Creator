"""
PromptBuilder Node

Builds text prompts for multi-view generation from templates.
"""
from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


_VIEW_PROMPT_TEMPLATES = {
    "front": "{trigger_word}, front view, full body, white background",
    "side": "{trigger_word}, side view, full body, white background",
    "back": "{trigger_word}, back view, full body, white background",
}

_DEFAULT_NEGATIVE = (
    "ugly, deformed, text, "
    "asymmetric eyes, deformed pupils, deformed mouth, "
    "extra fingers, mutated hands, bad anatomy, "
    "blurry face, distorted facial features"
)


@register_node
class PromptBuilderNode(BaseNode):
    NAME = "PromptBuilder"
    DISPLAY_NAME = "Prompt Builder"
    CATEGORY = "Text/Prompt"
    FUNCTION = "build"
    DESCRIPTION = "Build generation prompts from templates"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "trigger_word": ("STRING", {
                    "default": "character",
                    "label": "Trigger Word",
                }),
                "view_type": ("STRING", {
                    "default": "front",
                    "options": ["front", "side", "back", "custom"],
                    "label": "View Type",
                }),
                "prompt_template": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "label": "Custom Prompt (overrides template if set)",
                }),
                "negative_prompt": ("STRING", {
                    "default": _DEFAULT_NEGATIVE,
                    "multiline": True,
                    "label": "Negative Prompt",
                }),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {"prompt": PortType.STRING, "neg_prompt": PortType.STRING}

    def build(self, trigger_word: str, view_type: str,
              prompt_template: str, negative_prompt: str):
        if prompt_template.strip():
            prompt = prompt_template.format(trigger_word=trigger_word)
        else:
            template = _VIEW_PROMPT_TEMPLATES.get(
                view_type, _VIEW_PROMPT_TEMPLATES["front"]
            )
            prompt = template.format(trigger_word=trigger_word)

        neg = negative_prompt.strip() or _DEFAULT_NEGATIVE

        logger.info(f"[PromptBuilder] view={view_type}, prompt={prompt[:60]}...")
        return {"prompt": prompt, "neg_prompt": neg}
