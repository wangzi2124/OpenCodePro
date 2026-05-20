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
        ModelInfo("gpt-4.1", "GPT-4.1", "openai", 1048576, True, True, True, {"prompt": 0.002, "completion": 0.008}),
        ModelInfo("gpt-4.1-mini", "GPT-4.1 Mini", "openai", 1048576, True, True, True, {"prompt": 0.0004, "completion": 0.0016}),
        ModelInfo("gpt-4.1-nano", "GPT-4.1 Nano", "openai", 1048576, True, False, True, {"prompt": 0.0001, "completion": 0.0004}),
        ModelInfo("gpt-4o", "GPT-4o", "openai", 128000, True, True, True, {"prompt": 0.0025, "completion": 0.01}),
        ModelInfo("gpt-4o-mini", "GPT-4o Mini", "openai", 128000, True, True, True, {"prompt": 0.00015, "completion": 0.0006}),
        ModelInfo("o3-mini", "o3-mini", "openai", 200000, True, False, True, {"prompt": 0.0011, "completion": 0.0044}),
        ModelInfo("o4-mini", "o4-mini", "openai", 65536, True, False, True, {"prompt": 0.001, "completion": 0.004}),
    ],
    "anthropic": [
        ModelInfo("claude-sonnet-4-20250514", "Claude Sonnet 4", "anthropic", 200000, True, True, True, {"prompt": 0.003, "completion": 0.015}),
        ModelInfo("claude-3-5-sonnet-latest", "Claude 3.5 Sonnet", "anthropic", 200000, True, True, True, {"prompt": 0.003, "completion": 0.015}),
        ModelInfo("claude-3-5-haiku-latest", "Claude 3.5 Haiku", "anthropic", 200000, True, True, True, {"prompt": 0.0008, "completion": 0.004}),
        ModelInfo("claude-3-opus-latest", "Claude 3 Opus", "anthropic", 200000, True, True, True, {"prompt": 0.015, "completion": 0.075}),
    ],
    "ollama": [
        ModelInfo("qwen2.5:latest", "Qwen 2.5 (latest)", "ollama", 32768, True, False, True),
        ModelInfo("qwen2.5:32b", "Qwen 2.5 32B", "ollama", 32768, True, False, True),
        ModelInfo("qwen2.5-coder:latest", "Qwen 2.5 Coder", "ollama", 32768, True, False, True),
        ModelInfo("llama3.2:latest", "Llama 3.2", "ollama", 8192, True, False, True),
        ModelInfo("llama3.3:latest", "Llama 3.3", "ollama", 128000, True, False, True),
        ModelInfo("mistral:latest", "Mistral", "ollama", 8192, True, False, True),
        ModelInfo("mixtral:latest", "Mixtral", "ollama", 32768, True, False, True),
        ModelInfo("deepseek-r1:7b", "DeepSeek R1 7B", "ollama", 32768, True, False, True),
        ModelInfo("deepseek-coder-v2:latest", "DeepSeek Coder V2", "ollama", 65536, True, False, True),
        ModelInfo("codestral:latest", "Codestral", "ollama", 32768, True, False, True),
        ModelInfo("starcoder2:latest", "StarCoder2", "ollama", 16384, True, False, True),
        ModelInfo("phi4:latest", "Phi-4", "ollama", 16384, True, False, True),
        ModelInfo("gemma2:latest", "Gemma 2", "ollama", 8192, True, False, True),
    ],
    "openrouter": [
        ModelInfo("anthropic/claude-sonnet-4-20250514", "Claude Sonnet 4", "openrouter", 200000, True, True, True, {"prompt": 0.003, "completion": 0.015}),
        ModelInfo("openai/gpt-4.1", "GPT-4.1", "openrouter", 1048576, True, True, True, {"prompt": 0.002, "completion": 0.008}),
        ModelInfo("google/gemini-2.5-flash-preview-04-17", "Gemini 2.5 Flash", "openrouter", 1048576, True, True, True),
        ModelInfo("google/gemini-2.5-pro-preview-03-25", "Gemini 2.5 Pro", "openrouter", 1048576, True, True, True),
        ModelInfo("meta-llama/llama-4-maverick", "Llama 4 Maverick", "openrouter", 1048576, True, True, True),
        ModelInfo("deepseek/deepseek-chat", "DeepSeek V3", "openrouter", 65536, True, False, True),
        ModelInfo("deepseek/deepseek-r1", "DeepSeek R1", "openrouter", 65536, True, False, True),
        ModelInfo("qwen/qwen-2.5-coder-32b", "Qwen 2.5 Coder 32B", "openrouter", 32768, True, False, True),
    ],
    "groq": [
        ModelInfo("llama-3.3-70b-versatile", "Llama 3.3 70B", "groq", 128000, True, True, True, {"prompt": 0.00059, "completion": 0.00079}),
        ModelInfo("llama-3.1-8b-instant", "Llama 3.1 8B", "groq", 128000, True, True, True, {"prompt": 0.00005, "completion": 0.00008}),
        ModelInfo("mixtral-8x7b-32768", "Mixtral 8x7B", "groq", 32768, True, False, True),
        ModelInfo("deepseek-r1-distill-llama-70b", "DeepSeek R1 70B", "groq", 128000, True, False, True),
    ],
    "google": [
        ModelInfo("gemini-2.5-flash-preview-04-17", "Gemini 2.5 Flash", "google", 1048576, True, True, True),
        ModelInfo("gemini-2.5-pro-preview-03-25", "Gemini 2.5 Pro", "google", 1048576, True, True, True),
        ModelInfo("gemini-2.0-flash", "Gemini 2.0 Flash", "google", 1048576, True, True, True),
    ],
    "deepseek": [
        ModelInfo("deepseek-chat", "DeepSeek V3", "deepseek", 65536, True, False, True, {"prompt": 0.00027, "completion": 0.0011}),
        ModelInfo("deepseek-reasoner", "DeepSeek R1", "deepseek", 65536, True, False, True, {"prompt": 0.00055, "completion": 0.00219}),
    ],
    "together": [
        ModelInfo("meta-llama/Llama-3.3-70B-Instruct-Turbo", "Llama 3.3 70B", "together", 128000, True, False, True),
        ModelInfo("deepseek-ai/DeepSeek-V3", "DeepSeek V3", "together", 65536, True, False, True),
        ModelInfo("Qwen/Qwen2.5-Coder-32B-Instruct", "Qwen 2.5 Coder 32B", "together", 32768, True, False, True),
        ModelInfo("mistralai/Mixtral-8x22B-Instruct-v0.1", "Mixtral 8x22B", "together", 65536, True, False, True),
    ],
    "perplexity": [
        ModelInfo("sonar-pro", "Sonar Pro", "perplexity", 200000, True, False, True),
        ModelInfo("sonar", "Sonar", "perplexity", 200000, True, False, True),
    ],
    "xai": [
        ModelInfo("grok-2-latest", "Grok 2", "xai", 131072, True, False, True),
        ModelInfo("grok-3-latest", "Grok 3", "xai", 131072, True, False, True),
    ],
    "deepinfra": [
        ModelInfo("meta-llama/Llama-3.3-70B-Instruct-Turbo", "Llama 3.3 70B", "deepinfra", 128000, True, True, True),
        ModelInfo("Qwen/Qwen2.5-Coder-32B-Instruct", "Qwen 2.5 Coder 32B", "deepinfra", 32768, True, True, True),
    ],
    "mistral": [
        ModelInfo("codestral-latest", "Codestral", "mistral", 256000, True, False, True, {"prompt": 0.001, "completion": 0.003}),
        ModelInfo("mistral-large-latest", "Mistral Large", "mistral", 128000, True, True, True, {"prompt": 0.002, "completion": 0.006}),
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
        cached = LLMCache.get("openai", self.model, self.base_url, self.api_key)
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
        
        LLMCache.set("openai", self.model, client, self.base_url, self.api_key)
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
        cached = LLMCache.get("anthropic", self.model, api_key=self.api_key)
        if cached:
            return cached
        
        client = ChatAnthropic(
            model=self.model,
            api_key=self.api_key,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            max_retries=0,
        )
        
        LLMCache.set("anthropic", self.model, client, api_key=self.api_key)
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
        cached = LLMCache.get("ollama", self.model, self.base_url)
        if cached:
            return cached
        
        client = ChatOllama(
            model=self.model,
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
        )
        
        LLMCache.set("ollama", self.model, client, self.base_url)
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


class OpenAICompatibleProvider(BaseProvider):
    """Provider for any OpenAI-compatible API (Groq, Together, DeepSeek, Perplexity, xAI, etc.)"""
    def __init__(self, api_key: str = None, base_url: str = None, model: str = "gpt-4", timeout: float = 120.0):
        self.api_key = api_key or "not-needed"
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model
        self.timeout = timeout
    
    def _get_client(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            streaming=True,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            max_retries=0,
        )
    
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
        return {"content": response.content if hasattr(response, 'content') else str(response), "usage": {}}
    
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
        accumulated = ""
        async for chunk in self._get_client().astream(lc_messages):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if content:
                accumulated += content
                await callback(content)
        return {"content": accumulated, "usage": {}}
    
    def get_token_limit(self) -> int:
        for m in PROVIDER_MODELS.get("openai", []):
            if m.id == self.model:
                return m.context_length
        return 128000
    
    def supports_streaming(self) -> bool:
        return True


class ProviderManager:
    _providers: Dict[str, BaseProvider] = {}
    _default: str = "ollama"
    _config: Dict = {}
    
    @classmethod
    def configure(cls, config: Dict):
        cls._config = config
        
        # OpenAI
        cls._providers["openai"] = OpenAIProvider(
            api_key=config.get("openai", {}).get("api_key"),
            base_url=config.get("openai", {}).get("base_url") or "https://api.openai.com/v1",
            model=config.get("openai", {}).get("model", "gpt-4o"),
            timeout=config.get("openai", {}).get("timeout", 120.0),
        )
        
        # Anthropic
        cls._providers["anthropic"] = AnthropicProvider(
            api_key=config.get("anthropic", {}).get("api_key"),
            model=config.get("anthropic", {}).get("model", "claude-sonnet-4-20250514"),
            timeout=config.get("anthropic", {}).get("timeout", 120.0),
        )
        
        # Ollama
        cls._providers["ollama"] = OllamaProvider(
            base_url=config.get("ollama", {}).get("base_url", "http://localhost:11434"),
            model=config.get("ollama", {}).get("model", "qwen2.5:latest"),
            timeout=config.get("ollama", {}).get("timeout", 300.0),
        )
        
        # OpenRouter
        or_key = config.get("openrouter", {}).get("api_key") or os.getenv("OPENROUTER_API_KEY")
        if or_key:
            cls._providers["openrouter"] = OpenAICompatibleProvider(
                api_key=or_key,
                base_url=config.get("openrouter", {}).get("base_url", "https://openrouter.ai/api/v1"),
                model=config.get("openrouter", {}).get("model", "openai/gpt-4o"),
                timeout=config.get("openrouter", {}).get("timeout", 120.0),
            )
        
        # Google Gemini (OpenAI-compatible endpoint)
        google_key = config.get("google", {}).get("api_key") or os.getenv("GOOGLE_API_KEY")
        if google_key:
            cls._providers["google"] = OpenAICompatibleProvider(
                api_key=google_key,
                base_url=config.get("google", {}).get("base_url", "https://generativelanguage.googleapis.com/v1beta/openai/"),
                model=config.get("google", {}).get("model", "gemini-2.5-flash-preview-04-17"),
                timeout=config.get("google", {}).get("timeout", 120.0),
            )
        
        # OpenAI-compatible providers
        provider_configs = {
            "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
            "together": ("https://api.together.xyz/v1", "TOGETHER_API_KEY"),
            "deepseek": ("https://api.deepseek.com", "DEEPSEEK_API_KEY"),
            "perplexity": ("https://api.perplexity.ai", "PERPLEXITY_API_KEY"),
            "xai": ("https://api.x.ai/v1", "XAI_API_KEY"),
            "deepinfra": ("https://api.deepinfra.com/v1/openai", "DEEPINFRA_API_KEY"),
            "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
        }
        
        for provider_name, (base_url, env_key) in provider_configs.items():
            api_key = config.get(provider_name, {}).get("api_key") or os.getenv(env_key)
            if api_key:
                cls._providers[provider_name] = OpenAICompatibleProvider(
                    api_key=api_key,
                    base_url=config.get(provider_name, {}).get("base_url", base_url),
                    model=config.get(provider_name, {}).get("model", PROVIDER_MODELS.get(provider_name, [ModelInfo("default", "Default", provider_name)])[0].id),
                    timeout=config.get(provider_name, {}).get("timeout", 120.0),
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
        if is_local or (endpoint and ("localhost" in endpoint or "ollama" in endpoint)):
            return "ollama", cls.get_provider("ollama")
        
        if endpoint:
            for name, prov in cls._providers.items():
                if name != "ollama" and hasattr(prov, 'base_url') and endpoint == prov.base_url:
                    return name, prov
            
            if "openrouter" in endpoint:
                return "openrouter", OpenAICompatibleProvider(
                    api_key=cls._config.get("openrouter", {}).get("api_key") or os.getenv("OPENROUTER_API_KEY"),
                    base_url=endpoint,
                    model=model,
                )
            
            if "groq" in endpoint:
                return "groq", cls.get_provider("groq") or OpenAICompatibleProvider(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1", model=model)
            
            # Fallback: treat as OpenAI-compatible
            return "openai", OpenAIProvider(
                api_key=cls._config.get("openai", {}).get("api_key"),
                base_url=endpoint,
                model=model,
            )
        
        if model.startswith("claude"):
            return "anthropic", cls.get_provider("anthropic")
        
        if model.startswith("gpt") or model.startswith("o3") or model.startswith("o4"):
            return "openai", cls.get_provider("openai")
        
        if model.startswith("gemini"):
            return "google", cls.get_provider("google") or OpenAIProvider(base_url="https://generativelanguage.googleapis.com/v1beta/openai/", model=model, api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Check if model matches a specific provider
        model_lower = model.lower()
        provider_model_map = {
            "groq": ["llama-3.3", "llama-3.1", "mixtral", "deepseek-r1-distill"],
            "deepseek": ["deepseek-chat", "deepseek-reasoner", "deepseek/"],
            "together": ["together"],
            "perplexity": ["sonar"],
            "xai": ["grok"],
            "deepinfra": ["deepinfra"],
            "mistral": ["mistral", "codestral", "pixtral"],
            "openrouter": ["openrouter", "/"],
        }
        
        for provider_name, keywords in provider_model_map.items():
            if any(kw in model_lower for kw in keywords):
                prov = cls.get_provider(provider_name)
                if prov:
                    return provider_name, prov
        
        return cls._default, cls.get_provider(cls._default)
    
    @classmethod
    def create_streaming_llm(cls, model: str, endpoint: str = None, is_local: bool = True) -> BaseProvider:
        if is_local or (endpoint and ("localhost" in endpoint or "ollama" in endpoint)):
            return OllamaProvider(
                base_url=endpoint or "http://localhost:11434",
                model=model,
            )
        
        if endpoint:
            return OpenAIProvider(
                base_url=endpoint,
                model=model,
                api_key=cls._config.get("openai", {}).get("api_key") or "not-needed",
            )
        
        if model.startswith("claude"):
            return AnthropicProvider(model=model)
        
        return OpenAIProvider(model=model)


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
        "groq": {
            "api_key": os.getenv("GROQ_API_KEY", ""),
        },
        "together": {
            "api_key": os.getenv("TOGETHER_API_KEY", ""),
        },
        "deepseek": {
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        },
        "perplexity": {
            "api_key": os.getenv("PERPLEXITY_API_KEY", ""),
        },
        "xai": {
            "api_key": os.getenv("XAI_API_KEY", ""),
        },
        "deepinfra": {
            "api_key": os.getenv("DEEPINFRA_API_KEY", ""),
        },
        "mistral": {
            "api_key": os.getenv("MISTRAL_API_KEY", ""),
        },
    }
    
    ProviderManager.configure(config)


__all__ = [
    "ProviderManager",
    "BaseProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "ProviderType",
    "ModelInfo",
    "PROVIDER_MODELS",
    "RetryHandler",
    "LLMCache",
    "init_providers",
]