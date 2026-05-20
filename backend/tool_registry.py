import os
import re
import inspect
from typing import Any, Callable, Dict, List, Optional, get_type_hints
from dataclasses import dataclass
from pydantic import BaseModel, Field
from enum import Enum


class ToolType(str, Enum):
    FILE = "file"
    SEARCH = "search"
    WEB = "web"
    BASH = "bash"
    EDITOR = "editor"


class ToolCategory(str, Enum):
    FILE = "file"
    SEARCH = "search"
    WEB = "web"
    BASH = "bash"
    EDITOR = "editor"
    CUSTOM = "custom"


@dataclass
class ToolParameter:
    name: str
    type: str = "string"
    required: bool = True
    description: str = ""
    default: Any = None


class ToolDefinition(BaseModel):
    id: str = Field(..., description="Tool identifier")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Tool parameters schema")
    category: ToolCategory = Field(default=ToolCategory.FILE, description="Tool category")
    enabled: bool = Field(default=True, description="Whether tool is enabled")


class ToolInfo:
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        parameters: Dict[str, Dict[str, Any]],
        execute_fn: Callable,
        category: ToolCategory = ToolCategory.FILE,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.parameters = parameters
        self.execute_fn = execute_fn
        self.category = category

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = self.execute_fn.invoke(args) if hasattr(self.execute_fn, 'invoke') else self.execute_fn(**args)
            if inspect.iscoroutine(result):
                result = await result
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ToolRegistry:
    _tools: Dict[str, ToolInfo] = {}
    _custom_tools: List[ToolInfo] = []
    _initialized: bool = False

    @classmethod
    def register(cls, tool: ToolInfo):
        cls._tools[tool.id] = tool

    @classmethod
    def register_function(cls, func: Callable, id: str = None, category: ToolCategory = ToolCategory.FILE):
        tool_id = id or func.__name__
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or ""

        parameters = {}
        for param_name, param in sig.parameters.items():
            param_info = {
                "type": "string",
                "required": param.default == inspect.Parameter.empty,
                "description": cls._extract_param_description(doc, param_name),
            }
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            parameters[param_name] = param_info

        tool = ToolInfo(
            id=tool_id,
            name=tool_id,
            description=doc.split("\n")[0] if doc else "",
            parameters=parameters,
            execute_fn=func,
            category=category,
        )
        cls.register(tool)
        return func

    @staticmethod
    def _extract_param_description(doc: str, param_name: str) -> str:
        """Extract parameter description from docstring."""
        if not doc:
            return ""

        lines = doc.split("\n")
        in_args = False
        for line in lines:
            line = line.strip()
            if line.lower().startswith("args:") or line.lower().startswith("parameters:"):
                in_args = True
                continue
            if in_args:
                if line.startswith(param_name + ":") or line.startswith(param_name + " "):
                    rest = line[len(param_name):].strip(": ")
                    return rest
                elif line and not line.startswith("    ") and not line.startswith("\t"):
                    in_args = False

        return ""

    @classmethod
    def register_langchain_tools(cls, tools: List[Any]):
        """Register LangChain @tool decorated functions."""
        for t in tools:
            if hasattr(t, 'name') and hasattr(t, 'func'):
                cls.register_function(t.func, t.name, ToolCategory.FILE)

    @classmethod
    def get(cls, name: str) -> Optional[ToolInfo]:
        return cls._tools.get(name)

    @classmethod
    def list(cls) -> List[ToolInfo]:
        return list(cls._tools.values())

    @classmethod
    def list_by_category(cls, category: ToolCategory) -> List[ToolInfo]:
        return [t for t in cls._tools.values() if t.category == category]

    @classmethod
    def get_definitions(cls) -> Dict[str, ToolDefinition]:
        definitions = {}
        for tool in cls._tools.values():
            definitions[tool.id] = ToolDefinition(
                id=tool.id,
                description=tool.description,
                parameters=tool.parameters,
                category=tool.category,
            )
        return definitions

    @classmethod
    def get_schemas(cls) -> List[Dict]:
        schemas = []
        for tool in cls._tools.values():
            props = {}
            required = []
            for name, info in tool.parameters.items():
                prop = {"type": info.get("type", "string")}
                if "description" in info and info["description"]:
                    prop["description"] = info["description"]
                if "default" in info:
                    prop["default"] = info["default"]
                props[name] = prop
                if info.get("required", True):
                    required.append(name)

            schema = {
                "type": "function",
                "function": {
                    "name": tool.id,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                    },
                },
            }
            schemas.append(schema)
        return schemas

    @classmethod
    def get_tool_list_text(cls) -> str:
        tool_descriptions = []
        for tool in cls._tools.values():
            params_str = ", ".join(
                f"{name}{'(required)' if info.get('required') else ''}"
                for name, info in tool.parameters.items()
            )
            tool_descriptions.append(f"- {tool.id}({params_str}): {tool.description}")
        return "\n".join(tool_descriptions)


tool_registry = ToolRegistry()


def tool(name: str = None, category: ToolCategory = ToolCategory.FILE):
    def decorator(func: Callable) -> Callable:
        return tool_registry.register_function(func, name, category)
    return decorator


def init_tools():
    """Initialize and register all tools."""
    from backend.tools.chain_tools import TOOL_REGISTRY
    tool_registry.register_langchain_tools(TOOL_REGISTRY)