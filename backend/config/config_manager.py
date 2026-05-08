import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import yaml


class ConfigType(str, Enum):
    JSON = "json"
    YAML = "yaml"
    ENV = "env"


@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str = "build"
    model: str = "qwen2.5:latest"
    provider: str = "ollama"
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: List[str] = field(default_factory=list)
    permission: Dict = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """Provider configuration"""
    provider_id: str
    model_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class ToolConfig:
    """Tool configuration"""
    name: str
    enabled: bool = True
    config: Dict = field(default_factory=dict)


@dataclass
class MCPConfig:
    """MCP Server configuration"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict = field(default_factory=dict)


@dataclass
class OpenCodeConfig:
    """OpenCode configuration"""
    version: str = "1.0.0"
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    tools: Dict[str, ToolConfig] = field(default_factory=dict)
    mcp_servers: Dict[str, MCPConfig] = field(default_factory=dict)
    permission: Dict = field(default_factory=dict)
    project: Dict = field(default_factory=dict)


class ConfigManager:
    """Configuration manager"""
    
    _config: Optional[OpenCodeConfig] = None
    _config_path: str = ".opencode/config"
    _config_type: ConfigType = ConfigType.JSON
    
    @classmethod
    def load(cls, path: str = None) -> OpenCodeConfig:
        """Load configuration"""
        path = path or cls._config_path
        
        if os.path.exists(path):
            ext = os.path.splitext(path)[1]
            
            if ext in [".yaml", ".yml"]:
                cls._config_type = ConfigType.YAML
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
            else:
                with open(path, 'r') as f:
                    data = json.load(f)
            
            if data:
                cls._config = cls._parse_config(data)
                return cls._config
        
        cls._config = cls._default_config()
        return cls._config
    
    @classmethod
    def _parse_config(cls, data: Dict) -> OpenCodeConfig:
        """Parse config data"""
        agents = {}
        for name, agent_data in data.get("agents", {}).items():
            agents[name] = AgentConfig(**agent_data)
        
        providers = {}
        for name, provider_data in data.get("providers", {}).items():
            providers[name] = ProviderConfig(**provider_data)
        
        tools = {}
        for name, tool_data in data.get("tools", {}).items():
            tools[name] = ToolConfig(**tool_data)
        
        mcp = {}
        for name, mcp_data in data.get("mcp_servers", {}).items():
            mcp[name] = MCPConfig(**mcp_data)
        
        return OpenCodeConfig(
            version=data.get("version", "1.0.0"),
            agents=agents,
            providers=providers,
            tools=tools,
            mcp_servers=mcp,
            permission=data.get("permission", {}),
            project=data.get("project", {})
        )
    
    @classmethod
    def _default_config(cls) -> OpenCodeConfig:
        """Default configuration"""
        return OpenCodeConfig(
            version="1.0.0",
            agents={
                "build": AgentConfig(name="build", model="qwen2.5:latest"),
                "plan": AgentConfig(name="plan", model="qwen2.5:latest"),
            },
            providers={
                "ollama": ProviderConfig(
                    provider_id="ollama",
                    model_id="qwen2.5:latest",
                    base_url="http://localhost:11434"
                ),
                "openai": ProviderConfig(
                    provider_id="openai",
                    model_id="gpt-4",
                    base_url="https://api.openai.com/v1"
                ),
            }
        )
    
    @classmethod
    def save(cls, path: str = None):
        """Save configuration"""
        path = path or cls._config_path
        
        if not cls._config:
            cls._config = cls._default_config()
        
        data = {
            "version": cls._config.version,
            "agents": {name: asdict(agent) for name, agent in cls._config.agents.items()},
            "providers": {name: asdict(provider) for name, provider in cls._config.providers.items()},
            "tools": {name: asdict(tool) for name, tool in cls._config.tools.items()},
            "mcp_servers": {name: asdict(mcp) for name, mcp in cls._config.mcp_servers.items()},
            "permission": cls._config.permission,
            "project": cls._config.project,
        }
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        if path.endswith(".yaml") or path.endswith(".yml"):
            with open(path, 'w') as f:
                yaml.dump(data, f)
        else:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
    
    @classmethod
    def get(cls) -> OpenCodeConfig:
        """Get configuration"""
        if not cls._config:
            cls._config = cls.load()
        return cls._config
    
    @classmethod
    def get_agent(cls, name: str) -> Optional[AgentConfig]:
        """Get agent config"""
        return cls.get().agents.get(name)
    
    @classmethod
    def get_provider(cls, name: str) -> Optional[ProviderConfig]:
        """Get provider config"""
        return cls.get().providers.get(name)
    
    @classmethod
    def set_agent(cls, name: str, config: AgentConfig):
        """Set agent config"""
        cls.get().agents[name] = config
    
    @classmethod
    def set_provider(cls, name: str, config: ProviderConfig):
        """Set provider config"""
        cls.get().providers[name] = config


__all__ = ["ConfigManager", "OpenCodeConfig", "AgentConfig", "ProviderConfig", "ToolConfig", "MCPConfig", "ConfigType"]