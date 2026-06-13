"""
LLM Provider Registry

Defines supported LLM providers and their available models.
Uses database-first approach with fallback to hardcoded data.
Inspired by OneAPI's channel management approach.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy import select
from app.config.database import get_db_session_standalone
from app.models.llm_provider import LLMProvider, LLMModel
from app.utils.logger import logger


class ModelInfo(BaseModel):
    """Model information."""
    id: str  # Model identifier (e.g., "gpt-4", "claude-3-opus")
    name: str  # Display name
    max_tokens: int  # Maximum context window
    description: str = ""


class ProviderInfo(BaseModel):
    """LLM Provider information."""
    id: str  # Provider identifier (e.g., "openai", "anthropic")
    name: str  # Display name
    icon: str  # Font Awesome icon class (fallback)
    icon_url: str  # Path to provider logo image
    website: str  # Official website
    api_docs: str  # API documentation URL
    default_endpoint: str  # Default API endpoint
    requires_api_key: bool = True
    models: List[ModelInfo] = []


# Define all supported LLM providers
LLM_PROVIDERS: Dict[str, ProviderInfo] = {
    "openai": ProviderInfo(
        id="openai",
        name="OpenAI",
        icon="fa-brands fa-openai",
        icon_url="/providers/openai.svg",
        website="https://openai.com",
        api_docs="https://platform.openai.com/docs/api-reference",
        default_endpoint="https://api.openai.com",
        models=[
            ModelInfo(id="gpt-4o", name="GPT-4o", max_tokens=128000, description="Most capable model, fastest"),
            ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", max_tokens=128000, description="Affordable and intelligent small model"),
            ModelInfo(id="gpt-4-turbo", name="GPT-4 Turbo", max_tokens=128000, description="Previous high-intelligence model"),
            ModelInfo(id="gpt-4", name="GPT-4", max_tokens=8192, description="Original GPT-4"),
            ModelInfo(id="gpt-3.5-turbo", name="GPT-3.5 Turbo", max_tokens=16385, description="Fast, inexpensive model"),
        ],
    ),
    "anthropic": ProviderInfo(
        id="anthropic",
        name="Anthropic Claude",
        icon="fa-solid fa-brain",
        icon_url="/providers/anthropic.svg",
        website="https://www.anthropic.com",
        api_docs="https://docs.anthropic.com/claude/reference",
        default_endpoint="https://api.anthropic.com",
        models=[
            ModelInfo(id="claude-3-5-sonnet-latest", name="Claude 3.5 Sonnet", max_tokens=200000, description="Most intelligent Claude model"),
            ModelInfo(id="claude-3-5-haiku-latest", name="Claude 3.5 Haiku", max_tokens=200000, description="Fastest Claude model"),
            ModelInfo(id="claude-3-opus-latest", name="Claude 3 Opus", max_tokens=200000, description="Powerful Claude model"),
        ],
    ),
    "google": ProviderInfo(
        id="google",
        name="Google Gemini",
        icon="fa-brands fa-google",
        icon_url="/providers/google.svg",
        website="https://ai.google.dev",
        api_docs="https://ai.google.dev/api",
        default_endpoint="https://generativelanguage.googleapis.com",
        models=[
            ModelInfo(id="gemini-2.0-flash", name="Gemini 2.0 Flash", max_tokens=1048576, description="Latest Gemini model"),
            ModelInfo(id="gemini-1.5-pro", name="Gemini 1.5 Pro", max_tokens=2097152, description="High intelligence model"),
            ModelInfo(id="gemini-1.5-flash", name="Gemini 1.5 Flash", max_tokens=1048576, description="Fast, efficient model"),
        ],
    ),
    "deepseek": ProviderInfo(
        id="deepseek",
        name="DeepSeek",
        icon="fa-solid fa-robot",
        icon_url="/providers/deepseek.svg",
        website="https://www.deepseek.com",
        api_docs="https://platform.deepseek.com/api-docs",
        default_endpoint="https://api.deepseek.com",
        models=[
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat", max_tokens=128000, description="Powerful chat model"),
            ModelInfo(id="deepseek-coder", name="DeepSeek Coder", max_tokens=128000, description="Code-specialized model"),
            ModelInfo(id="deepseek-reasoner", name="DeepSeek Reasoner", max_tokens=128000, description="Reasoning-focused model"),
        ],
    ),
    "zhipu": ProviderInfo(
        id="zhipu",
        name="智谱 AI (Zhipu)",
        icon="fa-solid fa-wand-magic-sparkles",
        icon_url="/providers/zhipu.svg",
        website="https://www.zhipuai.cn",
        api_docs="https://open.bigmodel.cn/dev/api",
        default_endpoint="https://open.bigmodel.cn/api/paas/v4",
        models=[
            ModelInfo(id="glm-4.7", name="GLM-4.7", max_tokens=200000, description="High-intelligence model for Agentic Coding"),
            ModelInfo(id="glm-4", name="GLM-4", max_tokens=128000, description="Latest GLM model"),
            ModelInfo(id="glm-4v", name="GLM-4V", max_tokens=8192, description="Vision model"),
            ModelInfo(id="glm-3-turbo", name="GLM-3 Turbo", max_tokens=128000, description="Fast GLM model"),
        ],
    ),
    "dashscope": ProviderInfo(
        id="dashscope",
        name="通义千问 (Qwen)",
        icon="fa-solid fa-comments",
        icon_url="/providers/qwen.svg",
        website="https://tongyi.aliyun.com",
        api_docs="https://help.aliyun.com/zh/dashscope/developer-reference/api-details",
        default_endpoint="https://dashscope.aliyuncs.com",
        models=[
            ModelInfo(id="qwen-max", name="Qwen-Max", max_tokens=8000, description="Most capable Qwen model"),
            ModelInfo(id="qwen-plus", name="Qwen-Plus", max_tokens=131072, description="Balanced model"),
            ModelInfo(id="qwen-turbo", name="Qwen-Turbo", max_tokens=131072, description="Fast Qwen model"),
            ModelInfo(id="qwen-vl-max", name="Qwen-VL-Max", max_tokens=8000, description="Vision-language model"),
        ],
    ),
    "doubao": ProviderInfo(
        id="doubao",
        name="豆包 (Doubao)",
        icon="fa-solid fa-face-smile",
        icon_url="/providers/doubao.svg",
        website="https://www.doubao.com",
        api_docs="https://www.volcengine.com/docs/82379",
        default_endpoint="https://ark.cn-beijing.volces.com/api",
        models=[
            ModelInfo(id="doubao-pro-32k", name="Doubao Pro 32K", max_tokens=32000, description="Professional model"),
            ModelInfo(id="doubao-lite-32k", name="Doubao Lite 32K", max_tokens=32000, description="Lightweight model"),
        ],
    ),
    "ernie": ProviderInfo(
        id="ernie",
        name="文心一言 (ERNIE)",
        icon="fa-solid fa-brain",
        icon_url="/providers/ernie.svg",
        website="https://yiyan.baidu.com",
        api_docs="https://cloud.baidu.com/doc/WENXINWORKSHOP/s",
        default_endpoint="https://aip.baidubce.com",
        models=[
            ModelInfo(id="ernie-4.0-8k", name="ERNIE 4.0", max_tokens=8000, description="Latest ERNIEmodel"),
            ModelInfo(id="ernie-3.5-8k", name="ERNIE 3.5", max_tokens=8000, description="Previous version"),
            ModelInfo(id="ernie-speed-8k", name="ERNIE Speed", max_tokens=8000, description="Fast model"),
        ],
    ),
    "spark": ProviderInfo(
        id="spark",
        name="讯飞星火 (Spark)",
        icon="fa-solid fa-fire",
        icon_url="/providers/spark.svg",
        website="https://xinghuo.xfyun.cn",
        api_docs="https://www.xfyun.cn/doc/spark/Web.html",
        default_endpoint="https://spark-api-open.xf-yun.com",
        models=[
            ModelInfo(id="spark-max", name="Spark Max", max_tokens=8192, description="Most capable Spark model"),
            ModelInfo(id="spark-pro", name="Spark Pro", max_tokens=8192, description="Professional model"),
            ModelInfo(id="spark-lite", name="Spark Lite", max_tokens=4096, description="Lightweight model"),
        ],
    ),
    "ollama": ProviderInfo(
        id="ollama",
        name="Ollama (Local)",
        icon="fa-solid fa-server",
        icon_url="/providers/ollama.svg",
        website="https://ollama.com",
        api_docs="https://github.com/ollama/ollama/blob/main/docs/api.md",
        default_endpoint="http://localhost:11434",
        requires_api_key=False,
        models=[
            ModelInfo(id="llama3.1", name="Llama 3.1", max_tokens=8192, description="Meta's latest Llama"),
            ModelInfo(id="llama3", name="Llama 3", max_tokens=8192, description="Meta's Llama model"),
            ModelInfo(id="mistral", name="Mistral", max_tokens=8192, description="Mistral 7B model"),
            ModelInfo(id="qwen2.5", name="Qwen 2.5", max_tokens=32768, description="Alibaba's Qwen model"),
            ModelInfo(id="deepseek-r1", name="DeepSeek R1", max_tokens=32768, description="DeepSeek reasoning model"),
            ModelInfo(id="gemma2", name="Gemma 2", max_tokens=8192, description="Google's Gemma model"),
            ModelInfo(id="phi3", name="Phi-3", max_tokens=128000, description="Microsoft's Phi model"),
        ],
    ),
    "lmstudio": ProviderInfo(
        id="lmstudio",
        name="LM Studio (Local)",
        icon="fa-solid fa-desktop",
        icon_url="/providers/lmstudio.svg",
        website="https://lmstudio.ai",
        api_docs="https://lmstudio.ai/docs/api",
        default_endpoint="http://localhost:1234",
        requires_api_key=False,
        models=[
            ModelInfo(id="custom", name="Custom Model", max_tokens=8192, description="User-defined model"),
        ],
    ),
}


async def get_provider_by_id(provider_id: str) -> Optional[ProviderInfo]:
    """Get provider by ID from database, fallback to hardcoded data."""
    # Try database first
    try:
        async with get_db_session_standalone() as db:
            result = await db.execute(
                select(LLMProvider).where(
                    LLMProvider.code == provider_id,
                    LLMProvider.is_active == True
                )
            )
            db_provider = result.scalar_one_or_none()
            
            if db_provider:
                # Get models from database
                models_result = await db.execute(
                    select(LLMModel).where(
                        LLMModel.provider_id == db_provider.id,
                        LLMModel.is_active == True
                    ).order_by(LLMModel.sort_order)
                )
                db_models = models_result.scalars().all()
                
                # Convert to ProviderInfo
                return ProviderInfo(
                    id=db_provider.code,
                    name=db_provider.name_en,
                    icon=db_provider.icon_class or "fa-solid fa-robot",
                    icon_url=db_provider.icon_url or "",
                    website=db_provider.default_endpoint or "",
                    api_docs="",
                    default_endpoint=db_provider.default_endpoint or "",
                    requires_api_key=db_provider.requires_api_key,
                    models=[
                        ModelInfo(
                            id=m.code,
                            name=m.name,
                            max_tokens=m.max_tokens or 8192,
                            description=f"{m.name} model"
                        )
                        for m in db_models
                    ]
                )
    except Exception as e:
        logger.warning(f"Database query failed for provider {provider_id}, using hardcoded data: {e}")
    
    # Fallback to hardcoded data
    return LLM_PROVIDERS.get(provider_id)


async def get_all_providers() -> List[ProviderInfo]:
    """Get all active providers from database, fallback to hardcoded data."""
    providers = []
    
    # Try database first
    try:
        async with get_db_session_standalone() as db:
            result = await db.execute(
                select(LLMProvider)
                .where(LLMProvider.is_active == True)
                .order_by(LLMProvider.sort_order, LLMProvider.name_en)
            )
            db_providers = result.scalars().all()
            
            if db_providers:
                for db_provider in db_providers:
                    # Get models for this provider
                    models_result = await db.execute(
                        select(LLMModel).where(
                            LLMModel.provider_id == db_provider.id,
                            LLMModel.is_active == True
                        ).order_by(LLMModel.sort_order)
                    )
                    db_models = models_result.scalars().all()
                    
                    providers.append(ProviderInfo(
                        id=db_provider.code,
                        name=db_provider.name_en,
                        icon=db_provider.icon_class or "fa-solid fa-robot",
                        icon_url=db_provider.icon_url or "",
                        website=db_provider.default_endpoint or "",
                        api_docs="",
                        default_endpoint=db_provider.default_endpoint or "",
                        requires_api_key=db_provider.requires_api_key,
                        models=[
                            ModelInfo(
                                id=m.code,
                                name=m.name,
                                max_tokens=m.max_tokens or 8192,
                                description=f"{m.name} model"
                            )
                            for m in db_models
                        ]
                    ))
                return providers
    except Exception as e:
        logger.warning(f"Database query failed for all providers, using hardcoded data: {e}")
    return list(LLM_PROVIDERS.values())


async def get_provider_models(provider_id: str) -> List[ModelInfo]:
    """Get all models for a specific provider from database, fallback to hardcoded data."""
    # Try database first
    try:
        async with get_db_session_standalone() as db:
            result = await db.execute(
                select(LLMProvider).where(LLMProvider.code == provider_id)
            )
            db_provider = result.scalar_one_or_none()
            
            if db_provider:
                models_result = await db.execute(
                    select(LLMModel).where(
                        LLMModel.provider_id == db_provider.id,
                        LLMModel.is_active == True
                    ).order_by(LLMModel.sort_order)
                )
                db_models = models_result.scalars().all()
                
                return [
                    ModelInfo(
                        id=m.code,
                        name=m.name,
                        max_tokens=m.max_tokens or 8192,
                        description=f"{m.name} model"
                    )
                    for m in db_models
                ]
    except Exception as e:
        logger.warning(f"Database query failed for provider models {provider_id}, using hardcoded data: {e}")
    
    # Fallback to hardcoded data
    provider = LLM_PROVIDERS.get(provider_id)
    return provider.models if provider else []


async def get_model_info(provider_id: str, model_id: str) -> Optional[ModelInfo]:
    """Get specific model info from a provider from database, fallback to hardcoded data."""
    models = await get_provider_models(provider_id)
    for model in models:
        if model.id == model_id:
            return model
    return None
