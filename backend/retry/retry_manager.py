import os
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps


class RetryStrategy(str, Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED = "fixed"


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    backoff_factor: float = 2.0


class RetryError(Exception):
    """Retry error"""
    pass


class RetryManager:
    """Retry manager - handles retry logic"""
    
    _retry_history: Dict[str, List[Dict]] = {}
    
    @classmethod
    def execute(cls, func: Callable, config: RetryConfig = None, *args, **kwargs) -> Any:
        """Execute function with retry"""
        config = config or RetryConfig()
        
        attempt = 0
        last_error = None
        
        while attempt < config.max_attempts:
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                last_error = e
                attempt += 1
                
                if attempt >= config.max_attempts:
                    raise RetryError(f"Failed after {attempt} attempts: {e}")
                
                # Calculate delay
                if config.strategy == RetryStrategy.LINEAR:
                    delay = config.initial_delay * attempt
                elif config.strategy == RetryStrategy.EXPONENTIAL:
                    delay = config.initial_delay * (config.backoff_factor ** (attempt - 1))
                else:
                    delay = config.initial_delay
                
                delay = min(delay, config.max_delay)
                time.sleep(delay)
        
        raise last_error
    
    @classmethod
    def record_attempt(cls, func_name: str, success: bool, error: str = None):
        """Record attempt for tracking"""
        if func_name not in cls._retry_history:
            cls._retry_history[func_name] = []
        
        cls._retry_history[func_name].append({
            "success": success,
            "error": error,
            "timestamp": time.time()
        })
    
    @classmethod
    def get_stats(cls, func_name: str = None) -> Dict:
        """Get retry statistics"""
        if func_name:
            attempts = cls._retry_history.get(func_name, [])
            return {
                "total": len(attempts),
                "success": sum(1 for a in attempts if a["success"]),
                "failure": sum(1 for a in attempts if not a["success"])
            }
        
        return {
            name: {
                "total": len(attempts),
                "success": sum(1 for a in attempts if a["success"]),
                "failure": sum(1 for a in attempts if not a["success"])
            }
            for name, attempts in cls._retry_history.items()
        }


def with_retry(config: RetryConfig = None):
    """Decorator for retry"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return RetryManager.execute(func, config, *args, **kwargs)
        return wrapper
    return decorator


__all__ = ["RetryManager", "RetryConfig", "RetryStrategy", "RetryError", "with_retry"]