"""
LLMText Node

Generates text content (stories, scripts, dialogue) using LLM models.
Wraps llm_manager.chat_completion() for use within FlowPipe workflows.
"""
from flowpipe.core.node import BaseNode
from flowpipe.core.registry import register_node
from flowpipe.core.types import PortType

from app.utils.logger import logger


_STORY_SYSTEM_PROMPT = """You are a professional scriptwriter for short AI-generated videos.
Create a healing, heartwarming story suitable for a short video.
Return the response in JSON format with the following structure:
{
  "title": "Story title",
  "description": "Brief story description",
  "scenes": [
    {
      "scene_number": 1,
      "description": "Scene description",
      "prompt": "Detailed image generation prompt",
      "duration": 3
    }
  ]
}"""


@register_node
class LLMTextNode(BaseNode):
    NAME = "LLMText"
    DISPLAY_NAME = "LLM Text Generation"
    CATEGORY = "Generate/Text"
    FUNCTION = "generate"
    OUTPUT_NODE = True
    DESCRIPTION = "Generate text content using LLM models"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "label": "User Prompt",
                }),
                "channel_id": ("INT", {
                    "default": 0,
                    "label": "LLM Channel ID",
                }),
            },
            "optional": {
                "system_prompt": ("STRING", {
                    "default": _STORY_SYSTEM_PROMPT,
                    "multiline": True,
                    "label": "System Prompt",
                }),
                "style": ("STRING", {
                    "default": "healing",
                    "options": ["healing", "comedy", "adventure", "romance", "slice_of_life"],
                    "label": "Style",
                }),
                "temperature": ("FLOAT", {
                    "default": 0.8,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1,
                    "label": "Temperature",
                }),
                "max_tokens": ("INT", {
                    "default": 2048,
                    "min": 64,
                    "max": 8192,
                    "label": "Max Tokens",
                }),
                "ip_name": ("STRING", {
                    "default": "",
                    "label": "IP Character Name",
                }),
            },
        }

    @classmethod
    def RETURN_TYPES(cls):
        return {"text": PortType.STRING}

    async def generate(self, prompt: str, channel_id: int,
                       system_prompt: str = "", style: str = "healing",
                       temperature: float = 0.8, max_tokens: int = 2048,
                       ip_name: str = ""):
        from app.core.llm_manager import llm_manager

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        sys_prompt = system_prompt.strip() or _STORY_SYSTEM_PROMPT

        user_prompt = f"Create a {style} story"
        if ip_name:
            user_prompt += f" featuring the character '{ip_name}'"
        user_prompt += f". Theme: {prompt}"

        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(f"[LLMText] channel={channel_id}, prompt={prompt[:60]}...")

        text = await llm_manager.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model_id=channel_id if channel_id > 0 else None,
        )

        logger.info(f"[LLMText] Generated {len(text)} chars")
        return {"text": text}
