import os
import inspect
from typing import Optional, List, Dict, Any


class ToolRegistry:
    """Registry for agent tools with auto-description generation"""
    _instance = None
    _tools: Dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register(self, func):
        self._tools[func.__name__] = func
        return func
    
    def get(self, name: str):
        return self._tools.get(name)
    
    def list_tools(self):
        result = []
        for name, func in self._tools.items():
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""
            params = {}
            for param_name, param in sig.parameters.items():
                default = param.default if param.default != inspect.Parameter.empty else None
                params[param_name] = {
                    "required": default is None,
                    "description": "",
                }
            result.append({
                "name": name,
                "description": doc.split("\n")[0] if doc else "",
                "parameters": params,
            })
        return result
    
    def get_tool_definitions(self):
        definitions = {}
        for name, func in self._tools.items():
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""
            params = {}
            for param_name, param in sig.parameters.items():
                default = param.default if param.default != inspect.Parameter.empty else None
                params[param_name] = {
                    "type": "string",
                    "required": default is None,
                    "description": doc,
                }
            definitions[name] = {
                "name": name,
                "description": doc,
                "parameters": params,
            }
        return definitions


registry = ToolRegistry.get_instance()


def read_file(file_path: str, offset: int = 0, limit: int = 2000):
    """Read file contents with optional offset and limit. Returns lines with 1-indexed line numbers."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    if os.path.isdir(file_path):
        entries = []
        for item in os.listdir(file_path):
            item_path = os.path.join(file_path, item)
            if os.path.isdir(item_path):
                entries.append(f"{item}/")
            else:
                entries.append(item)
        return {"entries": entries, "type": "directory"}
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        if offset > 0:
            lines = lines[offset:]
        
        if limit > 0:
            lines = lines[:limit]
        
        content_lines = []
        for i, line in enumerate(lines, start=offset + 1):
            line = line.rstrip('\n\r')
            if len(line) > 2000:
                line = line[:2000] + "..."
            content_lines.append(f"{i}: {line}")
        
        result = {
            "type": "file",
            "content": "\n".join(content_lines),
            "total_lines": total_lines,
            "returned_lines": len(content_lines),
        }
        return result
    except Exception as e:
        return {"error": str(e)}


registry.register(read_file)


def write_file(file_path: str, content: str):
    """Write content to a file, creating directories if needed"""
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "message": f"Written to {file_path}"}
    except Exception as e:
        return {"error": str(e)}


registry.register(write_file)


def edit_file(file_path: str, old_string: str, new_string: str):
    """Edit a file by replacing old_string with new_string. Uses exact string replacement. When editing text from Read tool output, ensure indentation is preserved exactly."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        count = content.count(old_string)
        if count == 0:
            return {"error": "old_string not found in file"}
        if count > 1:
            return {"error": f"Found multiple matches for old_string. Provide more surrounding lines to identify the correct match."}
        
        content = content.replace(old_string, new_string, 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "message": f"Edited {file_path}"}
    except Exception as e:
        return {"error": str(e)}


registry.register(edit_file)


def write_file_tool(file_path: str, content: str):
    """Write content to a file, overwriting existing file if any. Must use Read tool first for existing files."""
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": file_path}
    except Exception as e:
        return {"error": str(e)}


def question_tool(questions: list):
    """Ask user questions during execution. Allows gathering preferences, clarifying instructions, getting decisions on implementation choices, or offering choices."""
    return {"questions": questions, "note": "Question tool requires user interaction"}


registry.register(question_tool)


def webfetch_tool(url: str, format: str = "markdown", timeout: int = 60):
    """Fetch content from a URL. Takes URL and optional format (text/markdown/html). Returns content in specified format. Maximum timeout 120 seconds."""
    import httpx
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            if format == "html":
                return {"content": response.text, "format": "html"}
            elif format == "text":
                return {"content": response.text, "format": "text"}
            else:
                return {"content": response.text[:50000], "format": "markdown", "truncated": len(response.text) > 50000}
    except Exception as e:
        return {"error": str(e)}


registry.register(webfetch_tool)


def websearch_tool(query: str, numResults: int = 8, livecrawl: str = "fallback", type: str = "auto"):
    """Search the web using Exa AI for real-time web searches. Provides up-to-date information. Use current year (2026) when searching for current events."""
    return {"error": "Websearch requires external API integration", "query": query}


registry.register(websearch_tool)


def task_tool(description: str, prompt: str, subagent_type: str = "general"):
    """Launch a subagent to handle complex tasks autonomously. Available types: explore (fast, for finding files/answering code questions), general (for complex multi-step tasks)."""
    return {"note": "Task tool requires agent orchestration", "description": description}


registry.register(task_tool)


def todowrite_tool(todos: list):
    """Create and manage a structured todo list for current coding session. Helps track progress, organize complex tasks, and demonstrate thoroughness."""
    return {"todos": todos, "note": "Todo tool for task management"}


registry.register(todowrite_tool)


def skill_tool(name: str):
    """Load a specialized skill when task matches one of the available skills. Injects skill instructions and resources into current conversation."""
    return {"note": "Skill tool requires skill registry", "name": name}


def agent_kill(reason: str = ""):
    """终止当前agent执行。当任务已完成或遇到无法解决的问题时使用。返回 'TERMINATE' 表示终止成功。"""
    return "TERMINATE"


registry.register(skill_tool)
registry.register(agent_kill)
