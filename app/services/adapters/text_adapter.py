"""
Text Generation Adapter

Translates unified generation requests into LLM chat completion calls.
Supports story/script generation, dialogue, and other text content.
"""
from typing import List, Optional, Dict, Any

from app.services.adapters.base import BaseGenerationAdapter
from app.services.adapters.protocol import GenerationRequest, GenerationResponse, GenerationCapability
from app.core.llm_manager import llm_manager
from app.utils.logger import logger


class TextGenerationAdapter(BaseGenerationAdapter):
    """
    Adapter for text generation using LLM models.
    
    Translates the unified GenerationRequest into LLM chat completion calls
    via the existing llm_manager. Supports story generation, scripts,
    dialogue, and other text content.
    """

    def get_supported_capabilities(self) -> List[str]:
        return [GenerationCapability.TEXT_GENERATION, GenerationCapability.CHAT]

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate text content using LLM.
        
        Translates unified parameters:
        - prompt → user message
        - parameters.style → system prompt style
        - parameters.duration_seconds → story duration target
        - parameters.system_prompt → optional custom system prompt
        """
        try:
            params = request.parameters
            generation_type = params.get("text_type", "story")  # story, script, dialogue
            
            # Build system prompt based on text type
            system_prompt = params.get("system_prompt") or self._build_system_prompt(
                generation_type, request.style, params.get("duration_seconds", 10)
            )
            
            # Build user prompt
            user_prompt = self._build_user_prompt(
                request.prompt, request.ip_name, request.style, params
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            
            # Call LLM via the manager with the specified channel
            story_text = await llm_manager.chat_completion(
                messages=messages,
                temperature=params.get("temperature", 0.8),
                max_tokens=params.get("max_tokens", 2048),
                model_id=request.channel_id,
            )
            
            logger.info(f"Text generation completed via channel {request.channel_id}: {story_text[:100]}...")
            
            return GenerationResponse(
                status="success",
                output_type="text",
                content=story_text,
                metadata={
                    "channel_id": request.channel_id,
                    "generation_type": generation_type,
                    "style": request.style,
                    "parameters": params,
                },
            )
        
        except Exception as e:
            logger.error(f"Text generation failed via channel {request.channel_id}: {e}")
            return GenerationResponse(
                status="failed",
                output_type="text",
                error=str(e),
            )

    def _build_system_prompt(self, text_type: str, style: Optional[str], duration_seconds: int) -> str:
        """Build system prompt based on text generation type."""
        if text_type == "story":
            return f"""You are a professional scriptwriter for short AI-generated videos.
Create a {style or 'healing'} story suitable for a short video.
Return the response in JSON format with the following structure:
{{
  "title": "Story title",
  "description": "Brief story description",
  "scenes": [
    {{
      "scene_number": 1,
      "description": "Scene description",
      "prompt": "Detailed image generation prompt",
      "duration": 3
    }}
  ]
}}"""
        elif text_type == "script":
            return f"""You are a professional scriptwriter. Write a {style or 'engaging'} script for a {duration_seconds}-second video.
Format the script with scene descriptions and dialogue."""
        else:
            return f"You are a creative AI assistant. Generate {style or 'engaging'} content based on the user's request."

    def _build_user_prompt(
        self, 
        prompt: str, 
        ip_name: Optional[str], 
        style: Optional[str],
        params: Dict[str, Any],
    ) -> str:
        """Build user prompt from request parameters."""
        duration = params.get("duration_seconds", 10)
        user_prompt = f"Create a {duration}-second {style or 'healing'} story"
        if ip_name:
            user_prompt += f" featuring the character '{ip_name}'"
        user_prompt += f". Theme: {prompt}"
        return user_prompt
