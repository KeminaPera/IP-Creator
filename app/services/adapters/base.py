"""
Base Generation Adapter

Abstract base class defining the unified interface for all generation adapters.
Each concrete adapter translates the unified protocol to model-specific API calls.
"""
from abc import ABC, abstractmethod
from typing import List

from app.services.adapters.protocol import GenerationRequest, GenerationResponse


class BaseGenerationAdapter(ABC):
    """
    Abstract base class for generation adapters.
    
    Inspired by ComfyUI's node-based architecture where each node (adapter)
    has a unified input/output interface. Concrete adapters translate the
    unified GenerationRequest into model-specific API calls and normalize
    the output into a unified GenerationResponse.
    """

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Execute generation using the unified request protocol.
        
        Args:
            request: Unified generation request with prompt, type, and parameters
            
        Returns:
            Unified generation response with normalized output
        """
        pass

    @abstractmethod
    def get_supported_capabilities(self) -> List[str]:
        """
        Return the capability tags this adapter handles.
        
        Used by the dispatcher to route requests to the correct adapter.
        For example, TextAdapter returns ['text_generation', 'chat'].
        
        Returns:
            List of capability tag strings
        """
        pass

    def supports_capability(self, capability: str) -> bool:
        """Check if this adapter supports a given capability."""
        return capability in self.get_supported_capabilities()
