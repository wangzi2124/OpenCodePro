import os
import re
import ast
from typing import Optional
from langchain.tools import tool
from langchain_core.tools import BaseTool


@tool
def read_file(file_path: str, offset: int = 0, limit: int = 2000) -> str:
    """Read file contents with optional offset and limit. Returns lines with 1-indexed line numbers.
    
    Args:
        file_path: Absolute path to the file to read
        offset: Line number to start reading from (0-indexed), default 0
        limit: Maximum number of lines to read, default 2000
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total = len(lines)
        end = min(offset + limit, total)
        
        result = []
        for i in range(offset, end):
            result.append(f"{i+1}: {lines[i].rstrip()}")
        
        return "\n".join(result) + f"\n--- Showing lines {offset+1}-{end} of {total} ---"
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file, creating directories if needed.
    
    Args:
        file_path: Absolute path to the file to write
        content: Content to write to the file
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully written to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    """Edit a file by replacing old_string with new_string. Uses exact string replacement.
    
    Args:
        file_path: Absolute path to the file to edit
        old_string: The exact string to find and replace
        new_string: The new string to replace with
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_string not in content:
            return f"String not found in file: {old_string}"
        
        new_content = content.replace(old_string, new_string)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return f"Successfully edited {file_path}"
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error editing file: {str(e)}"


@tool
def glob_search(pattern: str, path: str = ".") -> str:
    """Fast file pattern matching tool. Supports glob patterns like "**/*.js" or "src/**/*.ts".
    
    Args:
        pattern: Glob pattern to match files against
        path: Directory to search in, default current directory
    """
    import glob as glob_module
    try:
        base_path = os.path.abspath(path)
        matches = glob_module.glob(os.path.join(base_path, pattern), recursive=True)
        
        if not matches:
            return f"No files matching {pattern} in {path}"
        
        return "\n".join(sorted(matches))
    except Exception as e:
        return f"Error searching: {str(e)}"


@tool  
def grep_search(pattern: str, include: str = "*", path: str = ".") -> str:
    """Fast content search tool using regular expressions.
    
    Args:
        pattern: Regex pattern to search for
        include: File pattern to include (e.g., "*.js", "*.{ts,tsx}")
        path: Directory to search in
    """
    import glob as glob_module
    try:
        base_path = os.path.abspath(path)
        files = glob_module.glob(os.path.join(base_path, "**", include), recursive=True)
        
        results = []
        for file_path in files:
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f):
                            if re.search(pattern, line):
                                results.append(f"{file_path}:{i+1}: {line.rstrip()}")
                except:
                    pass
        
        if not results:
            return f"No matches found for {pattern}"
        
        return "\n".join(results[:100])
    except Exception as e:
        return f"Error searching: {str(e)}"


@tool
def run_bash(command: str, workdir: str = None, timeout: int = 120) -> str:
    """Execute a bash/terminal command and return stdout/stderr.
    
    Args:
        command: Command to execute
        workdir: Working directory (optional)
        timeout: Timeout in seconds (default 120)
    """
    import subprocess
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir
        )
        output = result.stdout or result.stderr
        return output if output else "Command completed with no output"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error running command: {str(e)}"


@tool
def fetch_url(url: str) -> str:
    """Fetch web page content from a URL.
    
    Args:
        url: URL to fetch content from
    """
    import httpx
    try:
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        
        content = response.text[:10000]
        if len(response.text) > 10000:
            content += f"\n... (truncated, total {len(response.text)} chars)"
        return content
    except Exception as e:
        return f"Error fetching URL: {str(e)}"


@tool
def web_search(query: str) -> str:
    """Search the web for information.
    
    Args:
        query: Search query
    """
    return f"Web search not implemented. Use fetch_url to visit specific URLs. Query: {query}"


@tool
def agent_kill() -> str:
    """Terminate the current agent execution."""
    return "TERMINATE"


TOOL_REGISTRY = [read_file, write_file, edit_file, glob_search, grep_search, run_bash, fetch_url, web_search, agent_kill]