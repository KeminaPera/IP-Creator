"""
LLM Model Synchronization Service

Synchronizes model information from provider APIs and updates the database.
Supports multiple providers with different sync strategies.
"""
from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.llm_provider import LLMProvider, LLMModel
from app.utils.logger import logger


class LLMModelSyncService:
    """Synchronize models from provider APIs"""
    
    # Provider sync configurations
    PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = {
        "openai": {
            "api_url": "https://api.openai.com/v1/models",
            "auth_type": "bearer",  # bearer, api_key, param
            "requires_api_key": True,
            "filter_pattern": "gpt-",  # Only sync GPT models
        },
        "google": {
            "api_url": "https://generativelanguage.googleapis.com/v1beta/models",
            "auth_type": "param",
            "auth_param_name": "key",
            "requires_api_key": True,
            "filter_pattern": "gemini",
        },
        "anthropic": {
            "api_url": None,  # No public API
            "requires_api_key": False,
            "sync_strategy": "registry",  # Use hardcoded registry
        },
        "deepseek": {
            "api_url": None,
            "requires_api_key": False,
            "sync_strategy": "registry",
        },
        "zhipu": {
            "api_url": None,
            "requires_api_key": False,
            "sync_strategy": "modelscope",
            "organization": "zhipuai",
            "filter_capabilities": ["text_generation", "vision", "text_to_image", "text_to_video", "text_to_audio"]
        },
        "dashscope": {  # Qwen uses dashscope code
            "api_url": None,
            "requires_api_key": False,
            "sync_strategy": "modelscope",
            "organization": "qwenai",
            "filter_capabilities": ["text_generation", "vision", "text_to_image", "text_to_video", "text_to_audio"]
        },
    }
    
    @classmethod
    async def sync_provider_models(
        cls,
        db: AsyncSession,
        provider_code: str,
        api_key: Optional[str] = None,
    ) -> Dict:
        """
        Synchronize models from a specific provider.
        
        Args:
            db: Database session
            provider_code: Provider code (e.g., 'openai', 'google')
            api_key: Optional API key for providers that require it
            
        Returns:
            Dict with sync results (synced_count, new_models, updated_models, etc.)
        """
        logger.info(f"Starting model sync for provider: {provider_code}")
        
        # Get provider from database
        provider = await cls._get_provider(db, provider_code)
        if not provider:
            raise ValueError(f"Provider '{provider_code}' not found in database")
        
        # Get provider config
        config = cls.PROVIDER_CONFIGS.get(provider_code)
        if not config:
            raise ValueError(f"No sync configuration for provider '{provider_code}'")
        
        # Check if API key is required
        if config.get("requires_api_key") and not api_key:
            raise ValueError(
                f"Provider '{provider_code}' requires an API key for synchronization. "
                f"Please enter your API key in the form."
            )
        
        # Sync based on strategy
        sync_strategy = config.get("sync_strategy", "api")
        
        if sync_strategy == "api":
            models_data = await cls._sync_from_api(config, api_key)
        elif sync_strategy == "registry":
            models_data = await cls._sync_from_registry(provider_code)
        elif sync_strategy == "modelscope":
            organization = config.get("organization")
            if not organization:
                raise ValueError(f"ModelScope sync requires 'organization' config for provider '{provider_code}'")
            models_data = await cls._sync_from_modelscope(organization)
        else:
            raise ValueError(f"Unknown sync strategy: {sync_strategy}")
        
        # Upsert models into database
        result = await cls._upsert_models(db, provider, models_data)
        
        logger.info(
            f"Sync completed for {provider_code}: "
            f"{result['synced_count']} new, {result['updated_count']} updated"
        )
        
        return result
    
    @classmethod
    async def _get_provider(
        cls, db: AsyncSession, provider_code: str
    ) -> Optional[LLMProvider]:
        """Get provider from database by code."""
        result = await db.execute(
            select(LLMProvider).where(LLMProvider.code == provider_code)
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def _sync_from_api(
        cls, config: Dict, api_key: Optional[str] = None
    ) -> List[Dict]:
        """Sync models from provider's API."""
        api_url = config["api_url"]
        auth_type = config.get("auth_type")
        
        headers = {}
        params = {}
        
        # Set up authentication
        if auth_type == "bearer" and api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif auth_type == "api_key" and api_key:
            headers["X-API-Key"] = api_key
        elif auth_type == "param" and api_key:
            param_name = config.get("auth_param_name", "key")
            params[param_name] = api_key
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
        
        # Parse models based on provider
        provider_code = next(
            k for k, v in cls.PROVIDER_CONFIGS.items() if v == config
        )
        
        if provider_code == "openai":
            return cls._parse_openai_models(data, config)
        elif provider_code == "google":
            return cls._parse_google_models(data, config)
        else:
            return []
    
    @classmethod
    def _parse_openai_models(cls, data: Dict, config: Dict) -> List[Dict]:
        """Parse OpenAI API response."""
        models = []
        filter_pattern = config.get("filter_pattern", "")
        
        for model_data in data.get("data", []):
            model_id = model_data.get("id", "")
            
            # Filter only chat models
            if filter_pattern and not model_id.startswith(filter_pattern):
                continue
            
            # Skip old/deprecated models
            if any(skip in model_id for skip in ["davinci", "curie", "babbage", "ada"]):
                continue
            
            models.append({
                "code": model_id,
                "name": model_id.replace("-", " ").title(),
                "max_tokens": 128000,  # Default, will be updated
                "description": f"OpenAI {model_id} model",
                "capabilities": ["text_generation", "chat"],
                "is_active": True,
            })
        
        return models
    
    @classmethod
    def _parse_google_models(cls, data: Dict, config: Dict) -> List[Dict]:
        """Parse Google Gemini API response."""
        models = []
        filter_pattern = config.get("filter_pattern", "")
        
        for model_data in data.get("models", []):
            model_name = model_data.get("name", "")  # e.g., "models/gemini-2.0-flash"
            
            # Extract model ID
            model_id = model_name.replace("models/", "")
            
            # Filter only Gemini models
            if filter_pattern and filter_pattern not in model_id:
                continue
            
            # Get max tokens
            max_tokens = model_data.get("maxOutputTokens", 0)
            
            models.append({
                "code": model_id,
                "name": model_id.replace("-", " ").title(),
                "max_tokens": max_tokens,
                "description": f"Google {model_id} model",
                "capabilities": ["text_generation", "chat", "vision"],
                "is_active": True,
            })
        
        return models
    
    @classmethod
    async def _sync_from_registry(cls, provider_code: str) -> List[Dict]:
        """
        Sync models from hardcoded registry.
        This is used for providers without public model list APIs.
        """
        from app.core.llm_provider_registry import LLM_PROVIDERS
        
        provider = LLM_PROVIDERS.get(provider_code)
        if not provider:
            logger.warning(f"Provider {provider_code} not found in registry")
            return []
        
        models = []
        for model in provider.models:
            models.append({
                "code": model.id,
                "name": model.name,
                "max_tokens": model.max_tokens,
                "description": model.description,
                "capabilities": ["text_generation", "chat"],
                "is_active": True,
            })
        
        logger.info(f"Loaded {len(models)} models from registry for {provider_code}")
        return models

    @classmethod
    async def _sync_from_modelscope(cls, organization: str) -> List[Dict]:
        """
        Sync models from ModelScope by organization.
        """
        url = "https://modelscope.cn/api/v1/models"
        params = {
            "organization": organization,
            "limit": "100"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
            models = []
            for model_data in data.get("models", []):
                # Skip if no essential fields
                if not model_data.get("id") or not model_data.get("name"):
                    continue
                    
                # Extract capabilities from tags and model ID
                capabilities = cls._extract_modelscope_capabilities(model_data)
                
                # Only include models with required capabilities
                if capabilities:
                    models.append({
                        "code": model_data["id"].replace("/", "-").replace(".", "-").replace("_", "-").lower(),
                        "name": model_data.get("name", model_data["id"]),
                        "description": model_data.get("description", ""),
                        "capabilities": capabilities,
                        "max_tokens": model_data.get("max_position_embeddings", 4096),
                        "is_active": True,
                        "release_date": model_data.get("last_modified", None),
                    })
            
            return models
            
        except Exception as e:
            logger.error(f"Error syncing from ModelScope for {organization}: {e}")
            return []

    @classmethod
    def _extract_modelscope_capabilities(cls, model_data: Dict) -> List[str]:
        """
        Extract capabilities from ModelScope model data.
        """
        capabilities = []
        model_id = model_data.get("id", "").lower()
        tags = model_data.get("tags", [])
        
        # Text generation models
        if any(kw in model_id or kw in str(tags).lower() 
               for kw in ["text", "llm", "chat", "glm", "qwen", "baichuan"]):
            capabilities.append("text_generation")
        
        # Vision/image models
        if any(kw in model_id or kw in str(tags).lower() 
               for kw in ["vision", "vl", "image", "sd", "stable-diffusion", "cogview"]):
            capabilities.append("text_to_image")
            capabilities.append("image_generation")
            capabilities.append("vision")
        
        # Video models
        if any(kw in model_id or kw in str(tags).lower() 
               for kw in ["video", "cogvideo", "animate", "sdxl-video"]):
            capabilities.append("text_to_video")
            capabilities.append("video_generation")
        
        # Audio models
        if any(kw in model_id or kw in str(tags).lower() 
               for kw in ["audio", "whisper", "tts", "music", "bark"]):
            capabilities.append("text_to_audio")
            capabilities.append("audio_generation")
        
        # Multi-modal
        if any(kw in model_id or kw in str(tags).lower() 
               for kw in ["multi-modal", "multimodal", "vlm", "vision-language"]):
            capabilities.append("multi_modal")
        
        return capabilities
    
    @classmethod
    async def _upsert_models(
        cls,
        db: AsyncSession,
        provider: LLMProvider,
        models_data: List[Dict],
    ) -> Dict:
        """
        Upsert models into database.
        Creates new models or updates existing ones.
        """
        new_count = 0
        updated_count = 0
        new_models = []
        updated_models = []
        
        for model_data in models_data:
            # Check if model already exists
            existing = await db.execute(
                select(LLMModel).where(
                    LLMModel.provider_id == provider.id,
                    LLMModel.code == model_data["code"],
                )
            )
            existing_model = existing.scalar_one_or_none()
            
            if existing_model:
                # Update existing model
                cls._update_model(existing_model, model_data)
                updated_count += 1
                updated_models.append(model_data["code"])
                logger.debug(f"Updated model: {model_data['code']}")
            else:
                # Create new model
                new_model = LLMModel(
                    provider_id=provider.id,
                    **model_data,
                )
                db.add(new_model)
                new_count += 1
                new_models.append(model_data["code"])
                logger.debug(f"Created new model: {model_data['code']}")
        
        # Update provider's last_synced_at timestamp (use local time)
        provider.last_synced_at = datetime.now()
        
        await db.commit()
        
        # Get total count
        result = await db.execute(
            select(LLMModel).where(LLMModel.provider_id == provider.id)
        )
        total_models = len(result.scalars().all())
        
        return {
            "provider": provider.code,
            "synced_count": new_count,
            "updated_count": updated_count,
            "new_models": new_models,
            "updated_models": updated_models,
            "total_models": total_models,
            "message": f"Successfully synced {new_count} new models, updated {updated_count} existing models",
        }
    
    @classmethod
    def _update_model(cls, model: LLMModel, data: Dict):
        """Update existing model with new data."""
        # Update fields if they have new values
        if data.get("name"):
            model.name = data["name"]
        if data.get("max_tokens"):
            model.max_tokens = data["max_tokens"]
        if data.get("description"):
            model.description = data["description"]
        if data.get("capabilities"):
            model.capabilities = data["capabilities"]
        if "is_active" in data:
            model.is_active = data["is_active"]


# Singleton instance
model_sync_service = LLMModelSyncService()
