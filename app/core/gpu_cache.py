"""
GPU Cache Module

Provides global singleton cache for GPU information to avoid redundant
CUDA initialization and torch imports across the application.

This cache is shared by:
- System health check (check_gpu)
- DiffusionService (device initialization)
- IPAdapterService (device initialization)
"""
from typing import Dict, Optional
from datetime import datetime
import threading
from app.utils.logger import logger


class GPUCache:
    """
    Global singleton cache for GPU information.
    
    Uses lazy loading pattern - GPU is only checked on first access,
    then cached in process memory for all subsequent calls.
    
    Thread-safe implementation using locks.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - ensure only one instance exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._cache = {}
        return cls._instance
    
    def get_info(self) -> Dict:
        """
        Get GPU information (with caching).
        
        Returns cached result if available, otherwise performs
        actual GPU check and caches the result.
        
        Returns:
            Dict containing GPU information:
            - cuda_available: bool - Whether CUDA is available
            - device_count: int - Number of GPU devices
            - device_name: str - GPU device name
            - total_memory_gb: float - Total GPU memory in GB
            - status: str - Health status (ok/warning/error)
            - message: str - Human-readable message
            - available: bool - Whether GPU is available
            - count: int - GPU count (alias for device_count)
            - memory_gb: float - Memory in GB (alias for total_memory_gb)
            - is_cached: bool - Whether result was from cache
            - cached_at: str - ISO format timestamp when cached
        """
        # Return cached result if already initialized
        if self._initialized:
            logger.debug("Returning cached GPU info")
            result = self._cache.copy()
            result["is_cached"] = True
            return result
        
        # Perform actual GPU check with thread safety
        with self._lock:
            # Double-check after acquiring lock
            if self._initialized:
                result = self._cache.copy()
                result["is_cached"] = True
                return result
            
            # Perform actual check
            self._cache = self._perform_gpu_check()
            self._initialized = True
            
            logger.info(
                f"GPU cache initialized: {self._cache.get('device_name', 'Unknown')} "
                f"({self._cache.get('total_memory_gb', 0):.1f} GB)"
            )
            
            result = self._cache.copy()
            result["is_cached"] = False
            return result
    
    def _perform_gpu_check(self) -> Dict:
        """
        Perform actual GPU hardware check.
        
        Returns:
            Dict containing GPU information
        """
        try:
            import torch
            
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                
                # Evaluate status based on memory
                status = "ok"
                if gpu_memory < 6:
                    status = "warning"
                
                return {
                    # Raw GPU info
                    "cuda_available": True,
                    "device_count": gpu_count,
                    "device_name": gpu_name,
                    "total_memory_gb": round(gpu_memory, 2),
                    
                    # Health check format
                    "status": status,
                    "message": f"GPU available: {gpu_name} ({gpu_memory:.1f} GB)",
                    "available": True,
                    "count": gpu_count,
                    "memory_gb": round(gpu_memory, 2),
                    
                    # Cache metadata
                    "cached_at": datetime.now().isoformat(),
                    "is_cached": False
                }
            else:
                return {
                    "cuda_available": False,
                    "device_count": 0,
                    "device_name": None,
                    "total_memory_gb": 0.0,
                    
                    "status": "warning",
                    "message": "No GPU available (using CPU - will be slow)",
                    "available": False,
                    "count": 0,
                    "memory_gb": 0.0,
                    
                    "cached_at": datetime.now().isoformat(),
                    "is_cached": False,
                    "impact": "Image/video generation will be very slow on CPU"
                }
                
        except ImportError:
            return {
                "cuda_available": False,
                "device_count": 0,
                "device_name": None,
                "total_memory_gb": 0.0,
                
                "status": "warning",
                "message": "PyTorch not installed",
                "available": False,
                "count": 0,
                "memory_gb": 0.0,
                
                "cached_at": datetime.now().isoformat(),
                "is_cached": False
            }
        except Exception as e:
            logger.error(f"GPU check failed: {e}")
            return {
                "cuda_available": False,
                "device_count": 0,
                "device_name": None,
                "total_memory_gb": 0.0,
                
                "status": "error",
                "message": f"Failed to check GPU: {str(e)}",
                "available": False,
                "count": 0,
                "memory_gb": 0.0,
                
                "cached_at": datetime.now().isoformat(),
                "is_cached": False
            }
    
    def invalidate(self):
        """
        Invalidate the cache.
        
        Forces next get_info() call to perform actual GPU check.
        Useful for testing or if GPU state changes (rare).
        """
        with self._lock:
            self._initialized = False
            self._cache = {}
            logger.info("GPU cache invalidated")
    
    def is_initialized(self) -> bool:
        """Check if cache has been initialized."""
        return self._initialized
    
    def get_cache_age_seconds(self) -> Optional[float]:
        """
        Get cache age in seconds.
        
        Returns:
            float: Age in seconds, or None if not cached
        """
        if not self._initialized or "cached_at" not in self._cache:
            return None
        
        cached_at = datetime.fromisoformat(self._cache["cached_at"])
        age = (datetime.now() - cached_at).total_seconds()
        return age


# Global singleton instance
gpu_cache = GPUCache()
