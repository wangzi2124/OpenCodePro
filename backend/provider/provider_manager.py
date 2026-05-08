import os
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import httpx
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RETRY_INITIAL_DELAY = 2.0
RETRY_BACKOFF_FACTOR = 2
RETRY_MAX_DELAY = 30.0

class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OBA = "obai"
    CUSTOM = "custom"


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    context_length: int = 4096
    supports_tools: bool = True
    supports_vision: bool = False
    supports_streaming: bool = True
    pricing: Dict = field(default_factory=dict)
    api_url: Optional[str] = None


PROVIDER_MODELS = {
    "openai": [
        ModelInfo("gpt-4", "GPT-4", "openai", 8192, True, True, True, {"prompt": 0.03, "completion": 0.06}),
        ModelInfo("gpt-4-turbo", "GPT-4 Turbo", "openai", 128000, True, True, True, {"prompt": 0.01, "completion": 0.03}),
        ModelInfo("gpt-3.5-turbo", "GPT-3.5 Turbo", "openai", 16385, True, False, True, {"prompt": 0.001, "completion": 0.002}),
        ModelInfo("o4-mini", "o4-mini", "openai", 65536, True, False, True, {"prompt": 0.001, "completion": 0.004}),
    ],
    "anthropic": [
        ModelInfo("claude-3-5-sonnet-latest", "Claude 3.5 Sonnet", "anthropic", 200000, True, True, True, {"prompt": 0.003, "completion": 0.015}),
        ModelInfo("claude-3-opus-latest", "Claude 3 Opus", "anthropic", 200000, True, True, True, {"prompt": 0.015, "completion": 0.075}),
        ModelInfo("claude-3-sonnet-latest", "Claude 3 Sonnet", "anthropic", 200000, True, True, True, {"prompt": 0.003, "completion": 0.015}),
        ModelInfo("claude-3-haiku-latest", "Claude 3 Haiku", "anthropic", 200000, True, True, True, {"prompt": 0.00025, "completion": 0.00125}),
    ],
    "ollama": [
        ModelInfo("qwen2.5:latest", "Qwen 2.5", "ollama", 32768, True, False, True),
        ModelInfo("qwen2.5:32b", "Qwen 2.5 32B", "ollama", 32768, True, False, True),
        ModelInfo("llama3:latest", "Llama 3", "ollama", 8192, True, False, True),
        ModelInfo("mistral:latest", "Mistral", "ollama", 8192, True, False, True),
        ModelInfo("deepseek-r1:7b", "DeepSeek R1 7B", "ollama", 32768, True, False, True),
        ModelInfo("minimax:9b", "MiniMax 9B", "ollama", 32768, True, False, True),
    ],
    "openrouter": [
        ModelInfo("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet (OpenRouter)", "openrouter", 200000, True, True, True, {"prompt": 0.003, "completion": 0.015}),
        ModelInfo("google/gemini-2.0-flash-exp", "Gemini 2.0 Flash", "openrouter", 32768, True, True, True),
        ModelInfo("meta-llama/llama-3.1-8b-instruct", "Llama 3.1 8B", "openrouter", 128000, True, True, True),
    ],
}


class LLMCache:
    _llm_instances: Dict[str, ChatOpenAI] = {}
    _last_used: Dict[str, float] = {}
    _max_cache_size = 10
    
    @classmethod
    def get_cache_key(cls, provider: str, model: str, base_url: Optional[str] = None, api_key: Optional[str] = None) -> str:
        parts = [provider, model]
        if base_url:
            parts.append(base_url)
        if api_key:
            parts.append(api_key[:8])
        return "|".join(parts)
    
    @classmethod
    def get(cls, provider: str, model: str, base_url: Optional[str] = None, api_key: Optional[str] = None) -> Optional[ChatOpenAI]:
        key = cls.get_cache_key(provider, model, base_url, api_key)
        if key in cls._llm_instances:
            cls._last_used[key] = time.time()
            return cls._llm_instances[key]
        return None
    
    @classmethod
    def set(cls, provider: str, model: str, llm: ChatOpenAI, base_url: Optional[str] = None, api_key: Optional[str] = None):
        key = cls.get_cache_key(provider, model, base_url, api_key)
        
        if len(cls._llm_instances) >= cls._max_cache_size:
            oldest_key = min(cls._last_used, key=cls._last_used.get)
            del cls._llm_instances[oldest_key]
            cls._last_used.pop(oldest_key, None)
        
        cls._llm_instances[key] = llm
        cls._last_used[key] = time.time()
    
    @classmethod
    def clear(cls):
        cls._llm_instances.clear()
        cls._last_used.clear()


class RetryHandler:
    @staticmethod
    def is_retryable(error: Exception, response_headers: Dict = None) -> Optional[str]:
        error_msg = str(error)
        error_type = type(error).__name__
        
        if "Overloaded" in error_msg or "overloaded" in error_msg:
            return "Provider is overloaded"
        if "too_many_requests" in error_msg or "rate_limit" in error_msg.lower():
            return "Too Many Requests"
        if "server_error" in error_msg.lower() or "exhausted" in error_msg.lower() or "unavailable" in error_msg.lower():
            return "Provider Server Error"
        
        if response_headers:
            retry_after_ms = response_headers.get("retry-after-ms") or response_headers.get("Retry-After-Ms")
            if retry_after_ms:
                return f"Retry after {float(retry_after_ms)/1000:.1f}s"
            
            retry_after = response_headers.get("retry-after") or response_headers.get("Retry-After")
            if retry_after:
                try:
                    return f"Retry after {float(retry_after):.1f}s"
                except:
                    pass
        
        return None
    
    @staticmethod
    def calculate_delay(attempt: int, error: Exception = None, response_headers: Dict = None) -> float:
        if response_headers:
            retry_after_ms = response_headers.get("retry-after-ms") or response_headers.get("Retry-After-Ms")
            if retry_after_ms:
                return min(float(retry_after_ms) / 1000, RETRY_MAX_DELAY)
            
            retry_after = response_headers.get("retry-after") or response_headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), RETRY_MAX_DELAY)
                except:
                    pass
        
        delay = RETRY_INITIAL_DELAY * (RETRY_BACKOFF_FACTOR ** (attempt - 1))
        return min(delay, RETRY_MAX_DELAY)
    
    @staticmethod
    async def sleep_with_abort(delay: float, abort_event=None):
        if abort_event:
            import asyncio
            try:
                await asyncio.wait_for(asyncio.sleep(delay), timeout=delay)
            except asyncio.TimeoutError:
                pass
        else:
            time.sleep(min(delay, 5))


class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, messages: List[Dict], **kwargs) -> Dict:
        pass
    
    @abstractmethod
    async def stream(self, messages: List[Dict], callback: Callable, **kwargs):
        pass
    
    @abstractmethod
    def get_token_limit(self) -> int:
        pass
    
    @abstractmethod
    def supports_streaming(self) -> bool:
        pass


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str = None, base_url: str = None, model: str = "gpt-4", timeout: float = 120.0):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "not-needed")
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model
        self.timeout = timeout
        self._client: Optional[ChatOpenAI] = None
    
    def _get_client(self) -> ChatOpenAI:
        cache_key = f"openai|{self.model}|{self.base_url}"
        
        cached = LLMCache.get("openai", self.model, self.base_url)
        if cached:
            return cached
        
        client = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            streaming=True,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            max_retries=0,
        )
        
        LLMCache.set("openai", self.model, self.base_url, self.api_key, client)
        return client
    
    async def complete(self, messages: List[Dict], **kwargs) -> Dict:
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(content=content, tool_call_id=msg.get("tool_call_id", "")))
        
        response = self._get_client().invoke(lc_messages)
        
        return {
            "content": response.content if hasattr(response, 'content') else str(response),
            "usage": getattr(response, 'usage', {})
        }
    
    async def stream(self, messages: List[Dict], callback: Callable, **kwargs):
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(content=content, tool_call_id=msg.get("tool_call_id", "")))
        
        client = self._get_client()
        
        accumulated = ""
        async for chunk in client.astream(lc_messages):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if content:
                accumulated += content
                await callback(content)
        
        return {"content": accumulated, "usage": {}}
    
    def get_token_limit(self) -> int:
        for m in PROVIDER_MODELS.get("openai", []):
            if m.id == self.model:
                return m.context_length
        return 8192
    
    def supports_streaming(self) -> bool:
        return True


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-latest", timeout: float = 120.0):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self._client = None
    
    def _get_client(self) -> ChatAnthropic:
        cache_key = f"anthropic|{self.model}"
        
        cached = LLMCache.get("anthropic", self.model)
        if cached:
            return cached
        
        client = ChatAnthropic(
            model=self.model,
            api_key=self.api_key,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            max_retries=0,
        )
        
        LLMCache.set("anthropic", self.model, api_key=self.api_key, llm=client)
        return client
    
    async def complete(self, messages: List[Dict], **kwargs) -> Dict:
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(content=content, tool_call_id=msg.get("tool_call_id", "")))
        
        response = self._get_client().invoke(lc_messages)
        
        return {
            "content": response.content if hasattr(response, 'content') else str(response),
            "usage": getattr(response, 'usage', {})
        }
    
    async def stream(self, messages: List[Dict], callback: Callable, **kwargs):
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(content=content, tool_call_id=msg.get("tool_call_id", "")))
        
        client = self._get_client()
        
        accumulated = ""
        async for chunk in client.astream(lc_messages):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if content:
                accumulated += content
                await callback(content)
        
        return {"content": accumulated, "usage": {}}
    
    def get_token_limit(self) -> int:
        for m in PROVIDER_MODELS.get("anthropic", []):
            if m.id == self.model:
                return m.context_length
        return 200000
    
    def supports_streaming(self) -> bool:
        return True


class OllamaProvider(BaseProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:latest", timeout: float = 300.0):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self._client = None
    
    def _get_client(self) -> ChatOllama:
        cache_key = f"ollama|{self.model}|{self.base_url}"
        
        cached = LLMCache.get("ollama", self.model, self.base_url)
        if cached:
            return cached
        
        client = ChatOllama(
            model=self.model,
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
        )
        
        LLMCache.set("ollama", self.model, self.base_url, llm=client)
        return client
    
    async def complete(self, messages: List[Dict], **kwargs) -> Dict:
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(content=content, tool_call_id=msg.get("tool_call_id", "")))
        
        response = self._get_client().invoke(lc_messages)
        
        return {
            "content": response.content if hasattr(response, 'content') else str(response),
            "usage": {}
        }
    
    async def stream(self, messages: List[Dict], callback: Callable, **kwargs):
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(content=content, tool_call_id=msg.get("tool_call_id", "")))
        
        client = self._get_client()
        
        accumulated = ""
        async for chunk in client.astream(lc_messages):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if content:
                accumulated += content
                await callback(content)
        
        return {"content": accumulated, "usage": {}}
    
    def get_token_limit(self) -> int:
        for m in PROVIDER_MODELS.get("ollama", []):
            if m.id == self.model:
                return m.context_length
        return 32768
    
    def supports_streaming(self) -> bool:
        return True


class ProviderManager:
    _providers: Dict[str, BaseProvider] = {}
    _default: str = "ollama"
    _config: Dict = {}
    
    @classmethod
    def configure(cls, config: Dict):
        cls._config = config
        
        cls._providers["openai"] = OpenAIProvider(
            api_key=config.get("openai", {}).get("api_key"),
            base_url=config.get("openai", {}).get("base_url") or "https://api.openai.com/v1",
            model=config.get("openai", {}).get("model", "gpt-4"),
            timeout=config.get("openai", {}).get("timeout", 120.0),
        )
        
        cls._providers["anthropic"] = AnthropicProvider(
            api_key=config.get("anthropic", {}).get("api_key"),
            model=config.get("anthropic", {}).get("model", "claude-3-5-sonnet-latest"),
            timeout=config.get("anthropic", {}).get("timeout", 120.0),
        )
        
        cls._providers["ollama"] = OllamaProvider(
            base_url=config.get("ollama", {}).get("base_url", "http://localhost:11434"),
            model=config.get("ollama", {}).get("model", "qwen2.5:latest"),
            timeout=config.get("ollama", {}).get("timeout", 300.0),
        )
    
    @classmethod
    def get_provider(cls, name: str = None) -> Optional[BaseProvider]:
        name = name or cls._default
        return cls._providers.get(name)
    
    @classmethod
    def get(cls, name: str = None) -> Optional[BaseProvider]:
        return cls.get_provider(name)
    
    @classmethod
    def set_default(cls, name: str):
        cls._default = name
    
    @classmethod
    def list_providers(cls) -> List[str]:
        return list(cls._providers.keys())
    
    @classmethod
    def list_models(cls, provider: str = None) -> List[ModelInfo]:
        return PROVIDER_MODELS.get(provider or cls._default, [])
    
    @classmethod
    def get_model_info(cls, model_id: str) -> Optional[ModelInfo]:
        for models in PROVIDER_MODELS.values():
            for model in models:
                if model.id == model_id:
                    return model
        
        if ":" in model_id:
            for models in PROVIDER_MODELS.values():
                for model in models:
                    if model.id.startswith(model_id.split(":")[0]):
                        return model
        
        return None
    
    @classmethod
    def resolve_provider(cls, model: str, endpoint: str = None, is_local: bool = False) -> tuple[str, BaseProvider]:
        if is_local or "localhost" in endpoint or "ollama" in endpoint:
            return "ollama", cls.get_provider("ollama")
        
        if endpoint and "openrouter" in endpoint:
            return "openrouter", OpenAIProvider(
                api_key=cls._config.get("openrouter", {}).get("api_key"),
                base_url=endpoint,
                model=model,
            )
        
        if model.startswith("gpt") or "openai" in endpoint:
            return "openai", cls.get_provider("openai")
        
        if model.startswith("claude"):
            return "anthropic", cls.get_provider("anthropic")
        
        return cls._default, cls.get_provider(cls._default)
    
    @classmethod
    def create_streaming_llm(cls, model: str, endpoint: str = None, is_local: bool = True) -> BaseProvider:
        if is_local or "localhost" in endpoint or "ollama" in endpoint:
            return OllamaProvider(
                base_url=endpoint or "http://localhost:11434",
                model=model,
            )
        
        if endpoint and ("openai" in endpoint or "openrouter" in endpoint):
            return OpenAIProvider(
                base_url=endpoint,
                model=model,
            )
        
        if model.startswith("claude"):
            return AnthropicProvider(model=model)
        
        return OllamaProvider(
            base_url=endpoint or "http://localhost:11434",
            model=model,
        )


def init_providers():
    config = {
        "ollama": {
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": os.getenv("OLLAMA_MODEL", "qwen2.5:latest"),
        },
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        },
        "anthropic": {
            "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        },
        "openrouter": {
            "api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "base_url": "https://openrouter.ai/api/v1",
        },
    }
    
    ProviderManager.configure(config)


__all__ = [
    "ProviderManager",
    "BaseProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "ProviderType",
    "ModelInfo",
    "PROVIDER_MODELS",
    "RetryHandler",
    "LLMCache",
    "init_providers",
]