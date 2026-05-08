import os
import re
import json
from typing import Optional
from langchain.tools import tool


TOOL_NAMES = [
    "read_file",
    "write_file", 
    "edit_file",
    "glob_search", 
    "grep_search",
    "run_bash",
    "fetch_url",
    "web_search"
]

SAFE_SHELL_COMMANDS = [
    "python",
    "node",
    "npm",
    "pip",
]


@tool
def read_file(file_path: str, offset: int = 0, limit: int = 2000) -> str:
    """Read file contents with optional offset and limit."""
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
    """Write content to a file. Use this to CREATE new files."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully written to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    """Edit file by replacing old_string with new_string."""
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
    """Fast file pattern matching."""
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
    """Fast content search tool."""
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
def run_bash(command: str, workdir: str = None, timeout: int = 120, confirm_id: str = None) -> str:
    """Execute command. Returns warning if confirmation needed, or executes if confirmed."""
    import subprocess
    from backend.permission.permission_manager import PermissionManager, DangerLevel, format_warning_message
    
    # Check command danger level
    warning = PermissionManager.check_command(command)
    
    # If safe, execute
    if warning.danger_level == DangerLevel.SAFE:
        return _execute_command(command, workdir, timeout)
    
    # If confirm_id provided and allowed, execute
    if confirm_id:
        confirmed = PermissionManager.confirm(confirm_id, True)
        if confirmed:
            return _execute_command(command, workdir, timeout)
        return "Command not confirmed"
    
    # Return warning
    if PermissionManager.needs_confirmation(warning):
        pending_id = PermissionManager.create_pending("session", warning)
        msg = format_warning_message(warning)
        msg += f"\n\nTo confirm, use confirm_id: {pending_id}"
        msg += f"\nOr call /api/permission/confirm with allow=true"
        return msg
    
    # Block critical
    if warning.danger_level == DangerLevel.CRITICAL:
        return f"⛔ BLOCKED: {warning.reason}"
    
    # Medium risk - return warning
    return format_warning_message(warning)


def _execute_command(command: str, workdir: str, timeout: int) -> str:
    """Execute command"""
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


@tool
def web_search(query: str) -> str:
    """Search the web."""
    return f"Web search not implemented. Query: {query}"


@tool
def batch_edit(edits: list) -> str:
    """Execute multiple file edits."""
    results = []
    for edit in edits:
        file_path = edit.get("file_path", "")
        old_string = edit.get("old_string", "")
        new_string = edit.get("new_string", "")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_string not in content:
                results.append(f"{file_path}: String not found")
                continue
            
            new_content = content.replace(old_string, new_string)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            results.append(f"{file_path}: Edited successfully")
        except Exception as e:
            results.append(f"{file_path}: Error - {e}")
    
    return "\n".join(results)


@tool
def todo_read() -> str:
    """Read the current todo list."""
    return "TODO feature not yet implemented."


@tool
def todo_write(content: str) -> str:
    """Write to the todo list."""
    return f"TODO: {content}"


@tool
def skill_list() -> str:
    """List available skills."""
    return "No skills loaded."


@tool
def skill_invoke(name: str, args: dict = None) -> str:
    """Invoke a skill by name."""
    return f"Skill '{name}' not found"


# Scaffolding tools
from langchain.tools import tool as langchain_tool


# create_vite_project tool
@langchain_tool
def create_vite_project(directory: str, template: str = "react", name: str = None) -> str:
    """Create a new Vite project (react/vue/vanilla).
    
    Args:
        directory: Full path where to create the project
        template: react, vue, vanilla, vue-ts, react-ts
        name: Project name (optional)
    """
    import json
    project_name = name or os.path.basename(directory)
    src_dir = os.path.join(directory, "src")
    
    try:
        os.makedirs(src_dir, exist_ok=True)
    except Exception as e:
        return f"Error: {e}"
    
    pkg = {
        "name": project_name,
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"}
    }
    
    is_react = template in ["react", "react-ts"]
    is_vue = template in ["vue", "vue-ts"]
    ext = "jsx" if is_react else "vue" if is_vue else "js"
    
    if is_react:
        pkg["dependencies"] = {"react": "^18.2.0", "react-dom": "^18.2.0"}
        pkg["devDependencies"] = {"@vitejs/plugin-react": "^4.2.1", "vite": "^5.1.0"}
        config = "import react from '@vitejs/plugin-react'\nexport default { plugins: [react()] }"
    elif is_vue:
        pkg["dependencies"] = {"vue": "^3.4.0"}
        pkg["devDependencies"] = {"@vitejs/plugin-vue": "^5.0.0", "vite": "^5.1.0"}
        config = "import vue from '@vitejs/plugin-vue'\nexport default { plugins: [vue()] }"
    else:
        pkg["devDependencies"] = {"vite": "^5.1.0"}
        config = "export default {}"
    
    with open(os.path.join(directory, "package.json"), "w") as f:
        json.dump(pkg, f, indent=2)
    
    with open(os.path.join(directory, "vite.config.js"), "w") as f:
        f.write(config)
    
    html = "<!DOCTYPE html><html><head><meta charset='UTF-8'/><title>" + project_name + "</title></head><body><div id='root'></div><script type='module' src='/src/main." + ext + "'></script></body></html>"
    with open(os.path.join(directory, "index.html"), "w") as f:
        f.write(html)
    
    if is_react:
        main_content = "import React from 'react'\nimport ReactDOM from 'react-dom/client'\nimport App from './App.jsx'\nimport './index.css'\nReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>)"
        app_content = "function App() {\n  return <div><h1>Hello " + project_name + "!</h1></div>\n}\nexport default App"
    else:
        main_content = "console.log('Hello " + project_name + "!')"
        app_content = main_content
    
    css = "* { margin: 0; padding: 0; box-sizing: border-box }\nbody { font-family: system-ui; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #1a1a2e; color: white }"
    
    with open(os.path.join(src_dir, "main." + ext), "w") as f:
        f.write(main_content)
    with open(os.path.join(src_dir, "App." + ext), "w") as f:
        f.write(app_content)
    with open(os.path.join(src_dir, "index.css"), "w") as f:
        f.write(css)
    with open(os.path.join(directory, ".gitignore"), "w") as f:
        f.write("node_modules\ndist\n.DS_Store")
    
    return f"Created Vite project at {directory}"


@langchain_tool
def install_dependencies(directory: str) -> str:
    """Install npm dependencies."""
    import subprocess
    import os
    
    # Normalize and validate path
    directory = os.path.abspath(str(directory))
    pkg_path = os.path.join(directory, "package.json")
    
    if not os.path.exists(pkg_path):
        return f"No package.json at {directory}"
    
    try:
        # Try PowerShell first (more reliable on Windows)
        cmd = f'cd "{directory}"; npm install'
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=180,
            shell=False
        )
        
        if result.returncode == 0:
            return f"Installed: {directory}"
        
        # Fallback to cmd
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode == 0:
            return f"Installed: {directory}"
        
        return f"Error: {result.stderr[:200]}"
    except Exception as e:
        return f"Error: {e}"


TOOL_REGISTRY = [
    read_file, write_file, edit_file, glob_search, grep_search, run_bash, 
    fetch_url, web_search, batch_edit, todo_read, todo_write, skill_list, skill_invoke,
    create_vite_project, install_dependencies
]