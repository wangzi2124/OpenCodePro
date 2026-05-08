import os
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum


class TokenType(str, Enum):
    PROMPT = "prompt"
    COMPLETION = "completion"
    TOTAL = "total"


@dataclass
class TokenUsage:
    """Token usage tracking"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class CostTracking:
    """Cost tracking"""
    model: str
    tokens: TokenUsage
    cost_per_1k_prompt: float = 0.0
    cost_per_1k_completion: float = 0.0
    
    @property
    def total_cost(self) -> float:
        """Calculate total cost"""
        prompt_cost = (self.tokens.prompt_tokens / 1000) * self.cost_per_1k_prompt
        completion_cost = (self.tokens.completion_tokens / 1000) * self.cost_per_1k_completion
        return prompt_cost + completion_cost


MODEL_PRICING = {
    "qwen2.5:latest": {"prompt": 0.0001, "completion": 0.0002},
    "qwen2.5:7b": {"prompt": 0.0001, "completion": 0.0002},
    "llama3": {"prompt": 0.0002, "completion": 0.0002},
    "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-3.5-turbo": {"prompt": 0.001, "completion": 0.002},
}


class TokenManager:
    """Token budget management"""
    
    MAX_TOKENS = 32000
    MAX_PROMPT_RATIO = 0.8  # 80% for prompt, 20% for completion
    
    _usage: Dict[str, TokenUsage] = {}
    _cost_history: Dict[str, float] = {}
    
    @classmethod
    def get_max_completion_tokens(cls, max_tokens: int = None) -> int:
        """Get max completion tokens"""
        max_tokens = max_tokens or cls.MAX_TOKENS
        return int(max_tokens * (1 - cls.MAX_PROMPT_RATIO))
    
    @classmethod
    def truncate_messages(cls, messages: list, max_tokens: int = None) -> list:
        """Truncate messages to fit budget"""
        max_tokens = max_tokens or cls.MAX_TOKENS
        
        # Estimate message count
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens <= max_tokens:
            return messages
        
        # Keep system + recent messages
        keep = int(len(messages) * (max_tokens / estimated_tokens))
        
        if messages and messages[0].get("role") == "system":
            return [messages[0]] + messages[-(keep-1):]
        
        return messages[-keep:]
    
    @classmethod
    def track_usage(cls, model: str, prompt_tokens: int, completion_tokens: int):
        """Track token usage"""
        if model not in cls._usage:
            cls._usage[model] = TokenUsage()
        
        usage = cls._usage[model]
        usage.prompt_tokens += prompt_tokens
        usage.completion_tokens += completion_tokens
    
    @classmethod
    def get_usage(cls, model: str = None) -> TokenUsage:
        """Get token usage"""
        if model:
            return cls._usage.get(model)
        
        total = TokenUsage()
        for usage in cls._usage.values():
            total.prompt_tokens += usage.prompt_tokens
            total.completion_tokens += usage.completion_tokens
        return total
    
    @classmethod
    def calculate_cost(cls, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for request"""
        pricing = MODEL_PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
        
        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]
        
        return prompt_cost + completion_cost
    
    @classmethod
    def get_model_pricing(cls, model: str) -> Dict:
        """Get model pricing"""
        return MODEL_PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
    
    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimate token count"""
        return len(text) // 4
    
    @classmethod
    def reset_usage(cls):
        """Reset usage tracking"""
        cls._usage.clear()
        cls._cost_history.clear()


__all__ = ["TokenManager", "TokenUsage", "MODEL_PRICING", "TokenType"]