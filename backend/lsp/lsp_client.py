import os
import json
import subprocess
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum


class LSPError(Exception):
    pass


class LSPStatus(str, Enum):
    NOT_STARTED = "not_started"
    STARTING = "starting"
    READY = "ready"
    ERROR = "error"


@dataclass
class LSPDiagnostic:
    """ LSP diagnostic """
    line: int
    column: int
    severity: int
    message: str
    source: Optional[str] = None


@dataclass
class LSPServer:
    """ LSP Server wrapper """
    name: str
    command: str
    args: List[str]
    status: LSPStatus = LSPStatus.NOT_STARTED
    capabilities: Dict = None
    process: Optional[subprocess.Popen] = None


LANGUAGE_SERVERS = {
    "python": {
        "command": "pylsp",
        "args": [],
    },
    "typescript": {
        "command": "typescript-language-server",
        "args": ["--stdio"],
    },
    "javascript": {
        "command": "typescript-language-server",
        "args": ["--stdio"],
    },
    "json": {
        "command": "vscode-json-languageserver",
        "args": ["--stdio"],
    },
    "rust": {
        "command": "rust-analyzer",
        "args": [],
    },
}


class LSPClient:
    """ Simple LSP client for language features """
    
    _servers: Dict[str, LSPServer] = {}
    _initialized: bool = False
    
    @classmethod
    def initialize(cls, project_dir: str = None):
        """ Initialize LSP for project """
        project_dir = project_dir or os.getcwd()
        
        if cls._initialized:
            return
        
        # Detect language and start appropriate server
        if os.path.exists(os.path.join(project_dir, "package.json")):
            cls._start_server("typescript", project_dir)
        
        if os.path.exists(os.path.join(project_dir, "pyproject.toml")) or \
           os.path.exists(os.path.join(project_dir, "requirements.txt")):
            cls._start_server("python", project_dir)
        
        cls._initialized = True
    
    @classmethod
    def _start_server(cls, language: str, project_dir: str):
        """ Start LSP server """
        server_config = LANGUAGE_SERVERS.get(language)
        if not server_config:
            return
        
        server = LSPServer(
            name=language,
            command=server_config["command"],
            args=server_config["args"],
            status=LSPStatus.STARTING
        )
        
        try:
            server.process = subprocess.Popen(
                [server.command] + server.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_dir
            )
            server.status = LSPStatus.READY
        except FileNotFoundError:
            server.status = LSPStatus.ERROR
        
        cls._servers[language] = server
    
    @classmethod
    async def diagnose(cls, file_path: str, language: str = None) -> List[LSPDiagnostic]:
        """ Get diagnostics for file """
        if not language:
            language = cls._detect_language(file_path)
        
        server = cls._servers.get(language)
        if not server or server.status != LSPStatus.READY:
            return []
        
        # Send textDocument/diagnostic request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "textDocument/diagnostic",
            "params": {
                "textDocument": {
                    "uri": f"file://{file_path}"
                }
            }
        }
        
        try:
            server.process.stdin.write((json.dumps(request) + "\n").encode())
            server.process.stdin.flush()
            
            # Read response (simplified)
            line = server.process.stdout.readline()
            if line:
                response = json.loads(line.decode())
                return cls._parse_diagnostics(response)
        except Exception:
            pass
        
        return []
    
    @classmethod
    def _detect_language(cls, file_path: str) -> str:
        """ Detect language from file extension """
        ext = os.path.splitext(file_path)[1]
        
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".json": "json",
            ".rs": "rust",
        }
        
        return lang_map.get(ext, "python")
    
    @classmethod
    def _parse_diagnostics(cls, response: Any) -> List[LSPDiagnostic]:
        """ Parse LSP diagnostic response """
        diagnostics = []
        
        result = response.get("result", {})
        items = result.get("items", []) if isinstance(result, dict) else []
        
        for item in items:
            diagnostic = LSPDiagnostic(
                line=item.get("range", {}).get("start", {}).get("line", 0),
                column=item.get("range", {}).get("start", {}).get("character", 0),
                severity=item.get("severity", 1),
                message=item.get("message", ""),
                source=item.get("source"),
            )
            diagnostics.append(diagnostic)
        
        return diagnostics
    
    @classmethod
    async def complete(cls, file_path: str, line: int, character: int) -> List[Dict]:
        """ Get completions """
        language = cls._detect_language(file_path)
        server = cls._servers.get(language)
        
        if not server or server.status != LSPStatus.READY:
            return []
        
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/completion",
            "params": {
                "textDocument": {"uri": f"file://{file_path}"},
                "position": {"line": line, "character": character}
            }
        }
        
        try:
            server.process.stdin.write((json.dumps(request) + "\n").encode())
            server.process.stdin.flush()
            
            line = server.process.stdout.readline()
            if line:
                response = json.loads(line.decode())
                return response.get("result", {}).get("items", [])
        except Exception:
            pass
        
        return []
    
    @classmethod
    def shutdown(cls):
        """ Shutdown all servers """
        for server in cls._servers.values():
            if server.process:
                server.process.terminate()
        cls._servers.clear()
        cls._initialized = False


__all__ = ["LSPClient", "LSPServer", "LSPDiagnostic", "LSPStatus"]