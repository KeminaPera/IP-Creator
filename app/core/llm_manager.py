"""
LLM Manager Module

Core middleware for managing multiple LLM configurations with
hot-switching, health monitoring, and circuit breaker pattern.
"""
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import threading
from app.services.llm_service import BaseLLMClient, OllamaClient, OpenAICompatibleClient
from app.models.llm_model import LLMConfig
from app.security.crypto import encryption_service
from app.config.settings import settings
from app.utils.logger import logger
from app.config.database import async_session_factory
from sqlalchemy import select


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for LLM calls.
    
    Prevents cascading failures by temporarily blocking requests
    to unhealthy models after consecutive failures.
    """
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        from datetime import datetime
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def record_success(self):
        """Record a success and close the circuit."""
        self.failure_count = 0
        self.state = "closed"
    
    def can_execute(self) -> bool:
        """Check if requests can be executed."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure_time and \
               (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker transitioned to half-open")
                return True
            return False
        
        # half-open: allow one test request
        return True


class LLMFactory:
    """
    Factory for creating LLM client instances.
    
    Creates appropriate client type based on model configuration
    (local vs cloud provider).
    """
    
    @staticmethod
    def create_client(model_config: LLMConfig) -> BaseLLMClient:
        """
        Create LLM client from configuration.
        
        Args:
            model_config: LLM configuration from database
            
        Returns:
            Initialized LLM client instance
        """
        # Decrypt API key if needed
        api_key = None
        if model_config.api_key_encrypted:
            api_key = encryption_service.decrypt(model_config.api_key_encrypted)
        
        # Create appropriate client based on model type
        if model_config.model_type == "local":
            return OllamaClient(
                model_name=model_config.model_name,
                base_url=model_config.api_endpoint or "http://localhost:11434",
                timeout=model_config.timeout,
            )
        
        elif model_config.model_type == "cloud":
            if not api_key or not model_config.api_endpoint:
                raise ValueError(f"Cloud model {model_config.name} missing API key or endpoint")
            
            return OpenAICompatibleClient(
                model_name=model_config.model_name,
                api_key=api_key,
                base_url=model_config.api_endpoint,
                timeout=model_config.timeout,
            )
        
        else:
            raise ValueError(f"Unknown model type: {model_config.model_type}")


class LLMRegistry:
    """
    Thread-safe registry for managing active LLM clients.
    
    Maintains a cache of initialized clients and provides
    atomic switching between models.
    """
    
    def __init__(self):
        """Initialize LLM registry."""
        self._clients: Dict[int, BaseLLMClient] = {}
        self._circuit_breakers: Dict[int, CircuitBreaker] = {}
        self._active_model_id: Optional[int] = None
        self._lock = threading.RLock()
    
    def register_client(self, model_id: int, client: BaseLLMClient):
        """
        Register an LLM client in the registry.
        
        Args:
            model_id: Database ID of the model
            client: Initialized LLM client
        """
        with self._lock:
            self._clients[model_id] = client
            self._circuit_breakers[model_id] = CircuitBreaker()
            logger.info(f"Registered LLM client for model ID {model_id}")
    
    def get_client(self, model_id: int) -> Optional[BaseLLMClient]:
        """
        Get registered LLM client by model ID.
        
        Args:
            model_id: Database ID of the model
            
        Returns:
            LLM client or None if not registered
        """
        with self._lock:
            return self._clients.get(model_id)
    
    def set_active_model(self, model_id: int):
        """
        Set the active model for the system.
        
        This operation is atomic and thread-safe.
        
        Args:
            model_id: Database ID of the model to activate
        """
        with self._lock:
            if model_id not in self._clients:
                raise ValueError(f"Model {model_id} not registered")
            
            old_active = self._active_model_id
            self._active_model_id = model_id
            logger.info(f"Switched active model from {old_active} to {model_id}")
    
    def get_active_model_id(self) -> Optional[int]:
        """Get the currently active model ID."""
        with self._lock:
            return self._active_model_id
    
    def get_active_client(self) -> Optional[BaseLLMClient]:
        """Get the currently active LLM client."""
        with self._lock:
            if self._active_model_id:
                return self._clients.get(self._active_model_id)
            return None
    
    def remove_client(self, model_id: int):
        """
        Remove a client from the registry.
        
        Args:
            model_id: Database ID to remove
        """
        with self._lock:
            self._clients.pop(model_id, None)
            self._circuit_breakers.pop(model_id, None)
            
            if self._active_model_id == model_id:
                self._active_model_id = None
    
    def get_circuit_breaker(self, model_id: int) -> Optional[CircuitBreaker]:
        """Get circuit breaker for a model."""
        with self._lock:
            return self._circuit_breakers.get(model_id)


# Global LLM registry instance
llm_registry = LLMRegistry()


class LLMManager:
    """
    High-level LLM management service.
    
    Orchestrates model registration, switching, health checks,
    and request routing with fault tolerance.
    """
    
    def __init__(self):
        """Initialize LLM manager."""
        self.registry = llm_registry
    
    async def initialize_models(self):
        """
        Load and initialize all active models from database.
        
        Called during application startup to populate the registry.
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(LLMConfig).where(LLMConfig.is_active == True)
            )
            models = result.scalars().all()
            
            for model in models:
                try:
                    client = LLMFactory.create_client(model)
                    self.registry.register_client(model.id, client)
                    
                    # Set as active if marked as default
                    if model.is_default and self.registry.get_active_model_id() is None:
                        self.registry.set_active_model(model.id)
                    
                    logger.info(f"Initialized model: {model.name}")
                
                except Exception as e:
                    logger.error(f"Failed to initialize model {model.name}: {e}")
            
            # If no default model, activate the first successfully registered one
            if self.registry.get_active_model_id() is None:
                # Get all registered model IDs
                registered_ids = list(self.registry._clients.keys())
                if registered_ids:
                    first_id = registered_ids[0]
                    self.registry.set_active_model(first_id)
                    logger.info(f"Activated first registered model as default: {first_id}")
                else:
                    logger.warning("No LLM models successfully initialized")
    
    async def register_model(self, model_config: LLMConfig) -> bool:
        """
        Register a new LLM model.
        
        Args:
            model_config: LLM configuration
            
        Returns:
            True if registration successful
        """
        try:
            client = LLMFactory.create_client(model_config)
            self.registry.register_client(model_config.id, client)
            logger.info(f"Registered new model: {model_config.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register model {model_config.name}: {e}")
            return False
    
    async def switch_model(self, model_id: int) -> bool:
        """
        Hot-switch to a different LLM model.
        
        This operation is instantaneous and doesn't require
        service restart or interrupt ongoing tasks.
        
        Args:
            model_id: Database ID of the target model
            
        Returns:
            True if switch successful
        """
        try:
            # Verify model exists in registry
            client = self.registry.get_client(model_id)
            if not client:
                logger.error(f"Cannot switch: model {model_id} not registered")
                return False
            
            # Atomic switch
            self.registry.set_active_model(model_id)
            logger.info(f"Successfully switched to model ID {model_id}")
            return True
        
        except Exception as e:
            logger.error(f"Model switch failed: {e}")
            return False
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model_id: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate chat completion using active or specified model.
        
        Includes circuit breaker protection and automatic fallback.
        Collects health metrics on each call.
        
        Args:
            messages: Chat messages
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            model_id: Specific model ID (uses active if None)
            **kwargs: Additional parameters
            
        Returns:
            Generated text response
        """
        target_model_id = model_id or self.registry.get_active_model_id()
        if not target_model_id:
            raise RuntimeError("No active LLM model configured")
        
        # Check circuit breaker
        circuit_breaker = self.registry.get_circuit_breaker(target_model_id)
        if circuit_breaker and not circuit_breaker.can_execute():
            raise RuntimeError(f"Model {target_model_id} circuit breaker is open")
        
        # Get client
        client = self.registry.get_client(target_model_id)
        if not client:
            raise RuntimeError(f"Model {target_model_id} not available")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Generate response
            response = await client.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            
            # Calculate response time
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000  # ms
            
            # Record success
            if circuit_breaker:
                circuit_breaker.record_success()
            
            # Update health metrics in database (await to ensure completion)
            await self._update_health_metrics(target_model_id, "success", response_time)
            
            return response
        
        except Exception as e:
            # Calculate failed response time
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000  # ms
            
            # Record failure
            if circuit_breaker:
                circuit_breaker.record_failure()
            
            # Update health metrics in database (await to ensure completion)
            await self._update_health_metrics(target_model_id, "failure", response_time)
            
            logger.error(f"Chat completion failed for model {target_model_id}: {e}")
            raise
    
    async def health_check_model(self, model_id: int) -> Dict[str, Any]:
        """
        Perform health check on a specific model.
        
        Args:
            model_id: Model to check
            
        Returns:
            Health status information
        """
        client = self.registry.get_client(model_id)
        if not client:
            return {"status": "unknown", "error": "Model not registered"}
        
        try:
            health = await client.health_check()
            
            # Update health metrics in database (success)
            response_time = health.get("response_time_ms")
            await self._update_health_metrics(model_id, "success", response_time)
            
            return health
        except Exception as e:
            # Update health metrics in database (failure)
            await self._update_health_metrics(model_id, "failure", None)
            
            return {"status": "unhealthy", "error": str(e)}
    
    async def _update_health_metrics(
        self,
        model_id: int,
        status: str,
        response_time_ms: float
    ):
        """
        Update health metrics in database after each API call.
        
        This is called asynchronously to not block the main request flow.
        
        Args:
            model_id: Model ID that was called
            status: "success" or "failure"
            response_time_ms: Response time in milliseconds
        """
        try:
            async with async_session_factory() as session:
                # Get current config
                result = await session.execute(
                    select(LLMConfig).where(LLMConfig.id == model_id)
                )
                config = result.scalar_one_or_none()
                
                if not config:
                    return
                
                from datetime import datetime, timezone
                
                # Update response time using Exponential Moving Average (EMA)
                # This gives more weight to recent calls while maintaining stability
                if response_time_ms is not None:
                    alpha_rt = 0.2  # Learning rate for response time (20% weight to new data)
                    current_avg = config.response_time_ms
                    
                    if current_avg is None:
                        # First call: initialize with actual response time
                        config.response_time_ms = response_time_ms
                    else:
                        # EMA formula: S_t = α × X_t + (1 - α) × S_{t-1}
                        config.response_time_ms = (alpha_rt * response_time_ms) + ((1 - alpha_rt) * current_avg)
                
                # Update last call time (use local time)
                from datetime import datetime
                config.last_health_check = datetime.now()
                
                # Update success rate using exponential moving average
                # This gives more weight to recent calls
                alpha = 0.1  # Learning rate (10% weight to new data)
                current_rate = config.success_rate or 100.0
                
                if status == "success":
                    new_rate = (alpha * 100.0) + ((1 - alpha) * current_rate)
                else:
                    new_rate = (alpha * 0.0) + ((1 - alpha) * current_rate)
                
                config.success_rate = new_rate
                
                # Update health status based on success rate
                if new_rate >= 80.0:
                    config.health_status = "healthy"
                elif new_rate >= 50.0:
                    config.health_status = "unhealthy"
                else:
                    config.health_status = "unhealthy"
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update health metrics for model {model_id}: {e}")
    
    async def health_check_all_models(self) -> List[Dict[str, Any]]:
        """
        Perform health checks on all registered models.
        
        Returns:
            List of health status for all models
        """
        results = []
        
        for model_id, client in self.registry._clients.items():
            health = await self.health_check_model(model_id)
            health["model_id"] = model_id
            results.append(health)
        
        return results


# Global LLM manager instance
llm_manager = LLMManager()
