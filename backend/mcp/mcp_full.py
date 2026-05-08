import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import httpx
from backend.tools.chain_tools import TOOL_REGISTRY


class MCPConnectionState(str, Enum):
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"


@dataclass
class MCPToolDefinition:
    """MCP tool definition"""
    name: str
    description: str
    input_schema: Dict = field(default_factory=dict)


@dataclass
class MCPResource:
    """MCP resource"""
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


@dataclass
class MCPProvider:
    """MCP provider for external model APIs"""
    
    name: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    model: str = "gpt-4"
    
    def __post_init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    async def complete(self, messages: List[Dict], **kwargs) -> Dict:
        """Send completion request"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()


class MCPClient:
    """Full MCP client implementation"""
    
    _servers: Dict[str, Dict] = {}
    _tools: List[MCPToolDefinition] = []
    _resources: List[MCPResource] = []
    _initialized: bool = False
    
    @classmethod
    def initialize(cls, project_dir: str = None):
        """Initialize MCP"""
        project_dir = project_dir or os.getcwd()
        
        mcp_config = cls._load_config(project_dir)
        
        for name, config in mcp_config.get("servers", {}).items():
            cls._servers[name] = {
                "command": config.get("command", ""),
                "args": config.get("args", []),
                "env": config.get("env", {}),
                "state": MCPConnectionState.INITIALIZING
            }
        
        cls._initialized = True
    
    @classmethod
    def _load_config(cls, project_dir: str) -> Dict:
        """Load MCP config"""
        config_path = os.path.join(project_dir, ".opencode", "mcp.json")
        
        if not os.path.exists(config_path):
            return {"servers": {}}
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    @classmethod
    async def connect(cls, server_name: str) -> bool:
        """Connect to MCP server"""
        server = cls._servers.get(server_name)
        
        if not server:
            return False
        
        # In full implementation, would spawn subprocess
        server["state"] = MCPConnectionState.READY
        return True
    
    @classmethod
    async def disconnect(cls, server_name: str):
        """Disconnect from MCP server"""
        server = cls._servers.get(server_name)
        
        if server:
            server["state"] = MCPConnectionState.INITIALIZING
    
    @classmethod
    def get_tools(cls) -> List[MCPToolDefinition]:
        """Get available tools"""
        return cls._tools
    
    @classmethod
    def get_resources(cls) -> List[MCPResource]:
        """Get available resources"""
        return cls._resources
    
    @classmethod
    async def list_tools(cls) -> List[Dict]:
        """List tools in MCP format"""
        tools = []
        
        for tool_def in cls._tools:
            tools.append({
                "name": tool_def.name,
                "description": tool_def.description,
                "input_schema": tool_def.input_schema
            })
        
        return tools
    
    @classmethod
    async def call_tool(cls, tool_name: str, arguments: Dict) -> str:
        """Call tool via MCP"""
        tool = next((t for t in cls._tools if t.name == tool_name), None)
        
        if not tool:
            return f"Tool not found: {tool_name}"
        
        # Execute tool
        for registry_tool in TOOL_REGISTRY:
            if registry_tool.name == tool_name:
                try:
                    return registry_tool.invoke(arguments)
                except Exception as e:
                    return f"Error: {e}"
        
        return f"Tool not implemented: {tool_name}"
    
    @classmethod
    def register_tool(cls, name: str, description: str, input_schema: Dict):
        """Register a tool"""
        tool = MCPToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema
        )
        cls._tools.append(tool)
    
    @classmethod
    def register_resource(cls, uri: str, name: str, description: str = None, mime_type: str = None):
        """Register a resource"""
        resource = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type
        )
        cls._resources.append(resource)


# Register common MCP providers
MCP_PROVIDERS = {
    "openai": MCPProvider(
        name="openai",
        base_url="https://api.openai.com/v1",
        model="gpt-4"
    ),
    "anthropic": MCPProvider(
        name="anthropic",
        base_url="https://api.anthropic.com/v1",
        model="claude-3-opus-20240229"
    ),
    "azure": MCPProvider(
        name="azure",
        base_url="",
        model=""
    ),
    "ollama": MCPProvider(
        name="ollama",
        base_url="http://localhost:11434/v1",
        model="qwen2.5:latest"
    ),
}


__all__ = ["MCPClient", "MCPProvider", "MCPToolDefinition", "MCPResource", "MCPConnectionState", "MCP_PROVIDERS"]