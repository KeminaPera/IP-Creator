"""
LLM Service Layer

Provides abstract base class and concrete implementations
for different LLM providers (Ollama, OpenAI-compatible APIs).
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import time
from app.utils.logger import logger


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM clients.
    
    Defines the interface that all LLM provider implementations
    must follow for consistent behavior across providers.
    """
    
    def __init__(self, model_name: str, **kwargs):
        """
        Initialize LLM client.
        
        Args:
            model_name: Name/identifier of the model
            **kwargs: Additional provider-specific parameters
        """
        self.model_name = model_name
        self.config = kwargs
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate chat completion from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (overrides default)
            max_tokens: Maximum tokens to generate (overrides default)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if the LLM service is healthy and responsive.
        
        Returns:
            Dict with health status information
        """
        pass
    
    def _prepare_parameters(self, temperature: Optional[float], max_tokens: Optional[int]) -> Dict[str, Any]:
        """
        Prepare generation parameters with defaults.
        
        Args:
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Dict of prepared parameters
        """
        params = {}
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        return params


class OllamaClient(BaseLLMClient):
    """
    Client for local Ollama LLM deployments.
    
    Connects to locally running Ollama service for offline,
    private LLM inference.
    """
    
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434", **kwargs):
        """
        Initialize Ollama client.
        
        Args:
            model_name: Ollama model name (e.g., "llama3", "qwen")
            base_url: Ollama API base URL
            **kwargs: Additional parameters
        """
        super().__init__(model_name, **kwargs)
        self.base_url = base_url
        self.client = None  # Will be initialized lazily
    
    async def _get_client(self):
        """Lazy initialization of Ollama client."""
        if self.client is None:
            import ollama
            self.client = ollama.AsyncClient(host=self.base_url)
        return self.client
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate chat completion using Ollama."""
        try:
            client = await self._get_client()
            params = self._prepare_parameters(temperature, max_tokens)
            
            response = await client.chat(
                model=self.model_name,
                messages=messages,
                options=params,
            )
            
            return response["message"]["content"]
        
        except Exception as e:
            logger.error(f"Ollama chat completion error: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama service health."""
        try:
            start_time = time.time()
            client = await self._get_client()
            
            # Try a simple request
            await client.list()
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "model": self.model_name,
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model_name,
            }


class OpenAICompatibleClient(BaseLLMClient):
    """
    Client for OpenAI-compatible API endpoints.
    
    Works with any provider that implements the OpenAI API spec
    (OpenAI, Zhipu, Qwen, etc.).
    """
    
    def __init__(
        self,
        model_name: str,
        api_key: str,
        base_url: str,
        **kwargs
    ):
        """
        Initialize OpenAI-compatible client.
        
        Args:
            model_name: Model identifier
            api_key: API authentication key
            base_url: API endpoint URL
            **kwargs: Additional parameters
        """
        super().__init__(model_name, **kwargs)
        self.api_key = api_key
        self.base_url = base_url
        self.client = None  # Will be initialized lazily
    
    async def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self.client is None:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self.client
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate chat completion using OpenAI-compatible API."""
        try:
            client = await self._get_client()
            params = self._prepare_parameters(temperature, max_tokens)
            
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **params,
                **kwargs,
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"OpenAI-compatible chat completion error: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API service health."""
        try:
            start_time = time.time()
            client = await self._get_client()
            
            # Try different methods to test connectivity
            # Method 1: Try models.list() (standard OpenAI API)
            try:
                await client.models.list()
                response_time = (time.time() - start_time) * 1000
                return {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "model": self.model_name,
                }
            except Exception:
                # Method 1 failed, try Method 2
                pass
            
            # Method 2: Try a minimal chat completion (for chat models)
            try:
                await client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "hi"}],
                    max_tokens=1,
                )
                response_time = (time.time() - start_time) * 1000
                return {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "model": self.model_name,
                }
            except Exception:
                # Method 2 failed, try Method 3
                pass
            
            # Method 3: Simple HTTP connectivity test to base URL
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as http_client:
                response = await http_client.get(self.base_url)
                # Any response (even 404/403) means the server is reachable
                if response.status_code < 500:  # Not a server error
                    response_time = (time.time() - start_time) * 1000
                    return {
                        "status": "healthy",
                        "response_time_ms": response_time,
                        "model": self.model_name,
                    }
            
            # All methods failed
            return {
                "status": "unhealthy",
                "error": "All health check methods failed",
                "model": self.model_name,
            }
        
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model_name,
            }
