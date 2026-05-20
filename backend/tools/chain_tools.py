import os
import asyncio
import base64
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from langchain.tools import tool as langchain_tool

from backend.tools.file_time import FileTime, FileNotReadError, FileModifiedError
from backend.tools.ripgrep_util import Ripgrep, Glob
from backend.tools.filesystem_util import Filesystem, is_binary_file, get_file_type
from backend.tools.edit_replacer import replace_content

WORK_DIR = os.getcwd()
MAX_LINE_LENGTH = 2000


class ToolResult:
    def __init__(self, title: str = "", output: str = "", metadata: Dict = None):
        self.title = title
        self.output = output
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "title": self.title,
            "output": self.output,
            "metadata": self.metadata
        }


@langchain_tool
def read_file(file_path: str, offset: int = 0, limit: int = 2000) -> str:
    """Read file contents with optional offset and limit.
    
    Args:
        file_path: Absolute path to the file
        offset: Line number to start reading from (0-based)
        limit: Number of lines to read (default 2000)
    """
    try:
        if not os.path.isabs(file_path):
            file_path = os.path.join(WORK_DIR, file_path)

        if not Filesystem.contains(WORK_DIR, file_path):
            return f"Error: Access denied - path escapes project directory"

        if not os.path.exists(file_path):
            parent_dir = os.path.dirname(file_path)
            if os.path.exists(parent_dir):
                entries = os.listdir(parent_dir)
                suggestions = [e for e in entries if file_path.lower() in e.lower() or e.lower() in file_path.lower()]
                if suggestions:
                    return f"File not found: {file_path}\n\nDid you mean one of these?\n" + "\n".join(suggestions[:3])
            return f"File not found: {file_path}"

        title = os.path.relpath(file_path, WORK_DIR)

        if is_binary_file(file_path):
            with open(file_path, "rb") as f:
                data = f.read(512 * 1024)
            mime = get_file_type(file_path)
            b64 = base64.b64encode(data).decode("utf-8")
            return f"Binary file: {title} ({mime})"

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total = len(lines)
        end = min(offset + limit, total)
        raw = lines[offset:end]

        formatted = []
        for i, line in enumerate(raw):
            line = line.rstrip("\n\r")
            if len(line) > MAX_LINE_LENGTH:
                line = line[:MAX_LINE_LENGTH] + "..."
            formatted.append(f"{offset + i + 1:05d}| {line}")

        content = "<file>\n" + "\n".join(formatted)

        if total > end:
            content += f"\n\n(File has more lines. Use 'offset' parameter to read beyond line {end})"
        else:
            content += f"\n\n(End of file - total {total} lines)"
        content += "\n</file>"

        return content

    except Exception as e:
        return f"Error reading file: {str(e)}"


@langchain_tool  
def write_file(file_path: str, content: str) -> str:
    """Write content to a file. Use this to CREATE or OVERWRITE files.
    
    Args:
        file_path: Absolute path to the file
        content: Content to write
    """
    try:
        if not os.path.isabs(file_path):
            file_path = os.path.join(WORK_DIR, file_path)

        if not Filesystem.contains(WORK_DIR, file_path):
            return f"Error: Access denied - path escapes project directory"

        exists = os.path.exists(file_path)
        
        if exists:
            file_stat = os.stat(file_path)
            if file_stat.st_size > 10 * 1024 * 1024:
                return f"Error: File too large (>10MB): {file_path}"

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        title = os.path.relpath(file_path, WORK_DIR)

        return f"Successfully written to {title}\n{file_path}"

    except Exception as e:
        return f"Error writing file: {str(e)}"


@langchain_tool
def edit_file(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Edit file by replacing old_string with new_string.
    
    Args:
        file_path: Absolute path to the file
        old_string: The text to replace (must be exact match)
        new_string: The text to replace it with
        replace_all: Replace all occurrences (default false)
    """
    try:
        if not os.path.isabs(file_path):
            file_path = os.path.join(WORK_DIR, file_path)

        if not Filesystem.contains(WORK_DIR, file_path):
            return f"Error: Access denied - path escapes project directory"

        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        if old_string == new_string:
            return "Error: oldString and newString must be different"

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        new_content, diff = replace_content(content, old_string, new_string, replace_all)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        title = os.path.relpath(file_path, WORK_DIR)

        return f"Edited {title}\n\n{diff}"

    except FileNotReadError as e:
        return f"Error: {str(e)}"
    except FileModifiedError as e:
        return f"Error: {str(e)}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error editing file: {str(e)}"


@langchain_tool
def glob_search(pattern: str, path: str = None) -> str:
    """Fast file pattern matching using ripgrep.
    
    Args:
        pattern: Glob pattern (e.g., "*.py", "src/**/*.ts")
        path: Directory to search in (default: current directory)
    """
    try:
        search_path = path or WORK_DIR
        if not os.path.isabs(search_path):
            search_path = os.path.join(WORK_DIR, search_path)

        if not Filesystem.contains(WORK_DIR, search_path):
            return "Error: Access denied - path escapes project directory"

        results = asyncio.run(Glob.search(pattern, search_path))

        if not results:
            return f"No files matching {pattern} in {path or 'current directory'}"

        rel_results = [os.path.relpath(r, search_path) for r in results[:100]]
        output = f"Found {len(rel_results)} files:\n" + "\n".join(rel_results)

        if len(results) > 100:
            output += f"\n(Results truncated. Consider using a more specific pattern.)"

        return output

    except Exception as e:
        return f"Error searching: {str(e)}"


@langchain_tool
def grep_search(pattern: str, include: str = None, path: str = None) -> str:
    """Fast content search using ripgrep.
    
    Args:
        pattern: Regex pattern to search for
        include: File pattern to include (e.g., "*.py")
        path: Directory to search in (default: current directory)
    """
    try:
        search_path = path or WORK_DIR
        if not os.path.isabs(search_path):
            search_path = os.path.join(WORK_DIR, search_path)

        if not Filesystem.contains(WORK_DIR, search_path):
            return "Error: Access denied - path escapes project directory"

        results = asyncio.run(Ripgrep.search(
            search_path,
            pattern,
            glob=include,
            limit=100
        ))

        if not results:
            return f"No matches found for '{pattern}'"

        output_lines = [f"Found {len(results)} matches"]

        current_file = ""
        for r in results:
            if current_file != r["path"]:
                current_file = r["path"]
                rel_path = os.path.relpath(current_file, search_path)
                output_lines.append(f"\n{rel_path}:")

            line_text = r["line_text"]
            if len(line_text) > MAX_LINE_LENGTH:
                line_text = line_text[:MAX_LINE_LENGTH] + "..."
            output_lines.append(f"  Line {r['line_num']}: {line_text}")

        return "\n".join(output_lines)

    except Exception as e:
        return f"Error searching: {str(e)}"


@langchain_tool
def run_bash(command: str, workdir: str = None, timeout: int = 120, confirm_id: str = None) -> str:
    """Execute command. Returns warning if confirmation needed, or executes if confirmed.
    
    Args:
        command: Shell command to execute
        workdir: Working directory (default: current directory)
        timeout: Timeout in seconds (default: 120)
        confirm_id: Confirmation ID if already approved
    """
    from backend.permission.permission_manager import PermissionManager, DangerLevel, format_warning_message
    
    warning = PermissionManager.check_command(command)
    
    if warning.danger_level == DangerLevel.SAFE:
        return _execute_command(command, workdir, timeout)
    
    if confirm_id:
        confirmed = PermissionManager.confirm(confirm_id, True)
        if confirmed:
            return _execute_command(command, workdir, timeout)
        return "Command not confirmed"
    
    if PermissionManager.needs_confirmation(warning):
        pending_id = PermissionManager.create_pending("session", warning)
        msg = format_warning_message(warning)
        msg += f"\n\nTo confirm, use confirm_id: {pending_id}"
        msg += f"\nOr call /api/permission/confirm with allow=true"
        return msg
    
    if warning.danger_level == DangerLevel.CRITICAL:
        return f"BLOCKED: {warning.reason}"
    
    return format_warning_message(warning)


def _execute_command(command: str, workdir: str, timeout: int) -> str:
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


@langchain_tool
def fetch_url(url: str) -> str:
    """Fetch web page content."""
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


@langchain_tool
def web_search(query: str) -> str:
    """Search the web."""
    return f"Web search not implemented. Query: {query}"


@langchain_tool
def batch_edit(edits: list) -> str:
    """Execute multiple file edits atomically.
    
    Args:
        edits: List of edit objects with file_path, old_string, new_string
    """
    results = []
    for edit in edits:
        file_path = edit.get("file_path", "")
        old_string = edit.get("old_string", "")
        new_string = edit.get("new_string", "")
        
        try:
            result = edit_file.invoke({
                "file_path": file_path,
                "old_string": old_string,
                "new_string": new_string
            })
            results.append(f"{file_path}: OK")
        except Exception as e:
            results.append(f"{file_path}: Error - {e}")
    
    return "\n".join(results)


@langchain_tool
def todo_read() -> str:
    """Read the current todo list."""
    return "TODO feature not yet implemented."


@langchain_tool
def todo_write(content: str) -> str:
    """Write to the todo list."""
    return f"TODO: {content}"


@langchain_tool
def skill_list() -> str:
    """List available skills."""
    return "No skills loaded."


@langchain_tool
def codesearch(query: str, path: str = None, include: str = None, max_results: int = 20) -> str:
    """Semantic code search - find code by concept using ripgrep-powered keyword matching.
    
    Args:
        query: Natural language description of what to find
        path: Directory to search in (default: current directory)
        include: File pattern to include (e.g., "*.py")
        max_results: Maximum results (default: 20)
    """
    try:
        search_path = path or WORK_DIR
        if not os.path.isabs(search_path):
            search_path = os.path.join(WORK_DIR, search_path)
        if not Filesystem.contains(WORK_DIR, search_path):
            return "Error: Access denied"

        # Extract keywords from query
        import re
        keywords = re.findall(r'\w+', query.lower())
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'shall', 'can',
                     'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'as', 'into', 'through', 'during', 'before', 'after', 'find',
                     'search', 'look', 'get', 'set', 'code', 'function', 'class'}
        keywords = [k for k in keywords if k not in stopwords and len(k) > 2][:5]

        if not keywords:
            return "No meaningful search terms extracted from query."

        results = asyncio.run(Ripgrep.search(
            search_path,
            pattern="|".join(keywords),
            glob=include,
            limit=max_results
        ))

        if not results:
            return f"No matches found for concepts in: {query}"

        output_lines = [f"Found {len(results)} semantic matches for '{query}':"]
        current_file = ""
        for r in results:
            if current_file != r["path"]:
                current_file = r["path"]
                rel_path = os.path.relpath(current_file, search_path)
                output_lines.append(f"\n{rel_path}:")
            line_text = r["line_text"]
            if len(line_text) > MAX_LINE_LENGTH:
                line_text = line_text[:MAX_LINE_LENGTH] + "..."
            output_lines.append(f"  Line {r['line_num']}: {line_text}")

        return "\n".join(output_lines)
    except Exception as e:
        return f"Error in codesearch: {str(e)}"


@langchain_tool
def multiedit(edits: list) -> str:
    """Make multiple targeted edits across multiple files in one operation.
    
    Args:
        edits: List of edit objects, each with:
            - file_path: Absolute path to the file
            - old_string: Exact text to replace
            - new_string: New text to insert
    """
    results = []
    all_success = True

    for i, edit in enumerate(edits):
        file_path = edit.get("file_path", "")
        old_string = edit.get("old_string", "")
        new_string = edit.get("new_string", "")
        marker = f"[{i+1}/{len(edits)}]"

        try:
            if not os.path.isabs(file_path):
                file_path = os.path.join(WORK_DIR, file_path)
            if not Filesystem.contains(WORK_DIR, file_path):
                results.append(f"{marker} {file_path}: Access denied")
                all_success = False
                continue
            if not os.path.exists(file_path):
                results.append(f"{marker} {file_path}: File not found")
                all_success = False
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                results.append(f"{marker} {file_path}: old_string not found")
                all_success = False
                continue

            new_content, diff = replace_content(content, old_string, new_string, False)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            rel_path = os.path.relpath(file_path, WORK_DIR)
            results.append(f"{marker} {rel_path}: OK")
        except Exception as e:
            results.append(f"{marker} {file_path}: Error - {e}")
            all_success = False

    status = "All edits applied" if all_success else "Some edits failed"
    return f"{status}\n" + "\n".join(results)


@langchain_tool
def lsp_diagnostics(file_path: str = None, language: str = None) -> str:
    """Get LSP diagnostics (errors/warnings) for a file or project.
    
    Args:
        file_path: Path to specific file (optional, checks all if omitted)
        language: Programming language (auto-detected from file extension)
    """
    try:
        from backend.tools.lsp_diagnostics import LSPDiagnostics
        search_path = file_path or WORK_DIR

        if file_path and not os.path.isabs(file_path):
            file_path = os.path.join(WORK_DIR, file_path)

        diagnostics = LSPDiagnostics.check(file_path or WORK_DIR, language)

        if not diagnostics:
            return "No diagnostics found."

        output_lines = [f"Found {len(diagnostics)} diagnostic(s):"]
        for d in diagnostics[:50]:
            sev = d.get("severity", "info").upper()
            file = d.get("file", "?")
            line = d.get("line", 0)
            msg = d.get("message", "")
            output_lines.append(f"  [{sev}] {file}:{line} - {msg}")

        if len(diagnostics) > 50:
            output_lines.append(f"\n... and {len(diagnostics) - 50} more")

        return "\n".join(output_lines)
    except ImportError:
        return "LSP diagnostics not available (lsp_diagnostics module required)"
    except Exception as e:
        return f"Error running diagnostics: {str(e)}"


@langchain_tool
def skill_invoke(name: str, args: dict = None) -> str:
    """Invoke a skill by name."""
    return f"Skill '{name}' not found"


@langchain_tool
def task_delegate(description: str, subtasks: list = None) -> str:
    """Delegate a subtask to a sub-agent.

    Use this to break complex tasks into parallel subtasks.
    The sub-agent will explore, analyze, or implement independently.

    Args:
        description: Clear description of what the sub-agent should do
        subtasks: Optional list of specific subtask descriptions

    Returns:
        Results from the sub-agent's execution
    """
    import json

    task_id = str(uuid.uuid4())[:8]
    subtask_list = subtasks or [description]

    # Store subtask for processing by the main loop
    from backend.storage.storage_manager import StorageManager
    StorageManager.set(f"subtask:{task_id}", {
        "id": task_id,
        "description": description,
        "subtasks": subtask_list,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    })

    return json.dumps({
        "task_id": task_id,
        "description": description,
        "subtask_count": len(subtask_list),
        "status": "pending",
        "message": f"Task {task_id} created. Execute using agent loop with task_id={task_id}"
    })


@langchain_tool
def task_status(task_id: str) -> str:
    """Check the status of a delegated subtask.

    Args:
        task_id: The task ID returned by task_delegate
    """
    from backend.storage.storage_manager import StorageManager
    task = StorageManager.get(f"subtask:{task_id}")
    if not task:
        return f"Task {task_id} not found"
    return f"Task {task_id}: {task.get('status', 'unknown')}\nResult: {task.get('result', 'pending')}"


TOOL_REGISTRY = [
    read_file, write_file, edit_file, glob_search, grep_search, run_bash,
    fetch_url, web_search, batch_edit, todo_read, todo_write,
    skill_list, skill_invoke, task_delegate, task_status,
    codesearch, multiedit, lsp_diagnostics,
]