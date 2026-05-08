import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pydantic import BaseModel
from enum import Enum


class MCPStatus(str, Enum):
    CONNECTED = "connected"
    DISABLED = "disabled"
    FAILED = "failed"
    NEEDS_AUTH = "needs_auth"


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    input_schema: Dict = field(default_factory=dict)
    execute: Optional[Callable] = None


@dataclass
class MCPServer:
    """MCP Server connection"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    status: MCPStatus = MCPStatus.DISABLED
    tools: List[MCPTool] = field(default_factory=list)


class MCPClient:
    """MCP Client for connecting to MCP servers"""
    
    _servers: Dict[str, MCPServer] = {}
    _initialized: bool = False
    
    @classmethod
    def initialize(cls, project_dir: str = None):
        if cls._initialized:
            return
        
        project_dir = project_dir or os.getcwd()
        
        # Load MCP servers from config
        cls._load_servers(project_dir)
        
        cls._initialized = True
    
    @classmethod
    def _load_servers(cls, project_dir: str):
        """Load MCP servers from .opencode/mcp.json"""
        mcp_file = os.path.join(project_dir, ".opencode", "mcp.json")
        
        if not os.path.exists(mcp_file):
            return
        
        try:
            with open(mcp_file, 'r', encoding='utf-8') as f:
                mcp_config = json.load(f)
            
            servers = mcp_config.get("servers", {})
            for name, config in servers.items():
                server = MCPServer(
                    name=name,
                    command=config.get("command", ""),
                    args=config.get("args", []),
                    env=config.get("env", {}),
                    status=MCPStatus.DISABLED,
                )
                cls._servers[name] = server
        except Exception:
            pass
    
    @classmethod
    def get(cls, name: str) -> Optional[MCPServer]:
        return cls._servers.get(name)
    
    @classmethod
    def list(cls) -> List[MCPServer]:
        return list(cls._servers.values())
    
    @classmethod
    async def connect(cls, name: str) -> bool:
        """Connect to an MCP server"""
        server = cls._servers.get(name)
        if not server:
            return False
        
        # For now, just mark as connected (full implementation would use MCP SDK)
        server.status = MCPStatus.CONNECTED
        return True
    
    @classmethod
    async def disconnect(cls, name: str):
        """Disconnect from an MCP server"""
        server = cls._servers.get(name)
        if server:
            server.status = MCPStatus.DISABLED
    
    @classmethod
    async def list_tools(cls) -> List[MCPTool]:
        """List all tools from connected MCP servers"""
        tools = []
        for server in cls._servers.values():
            if server.status == MCPStatus.CONNECTED:
                tools.extend(server.tools)
        return tools
    
    @classmethod
    async def call_tool(cls, server_name: str, tool_name: str, args: Dict) -> str:
        """Call a tool on an MCP server"""
        server = cls._servers.get(server_name)
        if not server or server.status != MCPStatus.CONNECTED:
            return f"MCP server '{server_name}' not connected"
        
        tool = next((t for t in server.tools if t.name == tool_name), None)
        if not tool:
            return f"Tool '{tool_name}' not found on server '{server_name}'"
        
        if tool.execute:
            try:
                return await tool.execute(args)
            except Exception as e:
                return f"Error: {e}"
        
        return f"Tool '{tool_name}' not implemented"


class MCPConfig(BaseModel):
    """MCP configuration model"""
    servers: Dict[str, Dict[str, Any]] = {}


__all__ = ["MCPClient", "MCPServer", "MCPTool", "MCPStatus", "MCPConfig"]