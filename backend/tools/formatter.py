import os
import re
from typing import Optional
from langchain.tools import tool


@tool
def format_code(file_path: str, language: str = None) -> str:
    """Format code file using language-specific formatter.
    
    Args:
        file_path: Absolute path to the file to format
        language: Programming language (python, javascript, typescript, etc.)
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if not language:
        language = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".json": "json",
            ".md": "markdown",
        }.get(ext, "text")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return f"Error reading file: {e}"
    
    formatted = content
    
    if language == "python":
        formatted = _format_python(content)
    elif language == "javascript":
        formatted = _format_javascript(content)
    elif language == "json":
        formatted = _format_json(content)
    
    if formatted != content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted)
            return f"Formatted {file_path} ({language})"
        except Exception as e:
            return f"Error writing file: {e}"
    
    return f"No changes needed for {file_path}"


def _format_python(content: str) -> str:
    """Simple Python formatter (PEP8 basics)"""
    lines = content.split('\n')
    formatted = []
    indent_level = 0
    
    for line in lines:
        stripped = line.rstrip()
        
        if not stripped:
            formatted.append('')
            continue
        
        # Decrease indent before dedent
        if stripped.startswith(('return', 'elif', 'else', 'except', 'finally', ')', ']')):
            indent_level = max(0, indent_level - 1)
        
        # Determine indent
        if stripped.startswith(('if ', 'elif ', 'else:', 'for ', 'while ', 'def ', 'class ', 'try:', 'except ', 'finally:')):
            formatted.append('    ' * indent_level + stripped)
            indent_level += 1
        else:
            formatted.append('    ' * indent_level + stripped)
        
        # Increase indent after colon
        if stripped.endswith(':') and not stripped.startswith('#'):
            indent_level += 1
    
    return '\n'.join(formatted)


def _format_javascript(content: str) -> str:
    """Simple JavaScript formatter"""
    lines = content.split('\n')
    formatted = []
    indent_level = 0
    
    for line in lines:
        stripped = line.rstrip()
        
        if not stripped:
            formatted.append('')
            continue
        
        # Handle braces
        if stripped.startswith('}'):
            indent_level = max(0, indent_level - 1)
        
        formatted.append('    ' * indent_level + stripped)
        
        if stripped.endswith('{'):
            indent_level += 1
    
    return '\n'.join(formatted)


def _format_json(content: str) -> str:
    """Format JSON"""
    import json
    try:
        data = json.loads(content)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        return content


@tool
def lint_code(file_path: str, language: str = None) -> str:
    """Lint code file for issues.
    
    Args:
        file_path: Absolute path to the file to lint
        language: Programming language
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if not language:
        language = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
        }.get(ext, "text")
    
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return f"Error reading file: {e}"
    
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Check for common issues
        if len(line) > 120:
            issues.append(f"Line {i}: Line too long ({len(line)} > 120)")
        
        if language == "python":
            if line.rstrip() != line.rstrip().replace('\t', '    '):
                issues.append(f"Line {i}: Use spaces instead of tabs")
            
            if 'print(' in line and not line.strip().startswith('#'):
                # Skip if in test file
                if not file_path.endswith('test.py'):
                    issues.append(f"Line {i}: Avoid print statements")
    
    if issues:
        return f"Issues found in {file_path}:\n" + '\n'.join(issues)
    
    return f"No issues found in {file_path}"


__all__ = ["format_code", "lint_code"]