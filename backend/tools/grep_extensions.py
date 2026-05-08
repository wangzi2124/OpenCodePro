import os
import re
from typing import Optional, List
from langchain.tools import tool


@tool
def replace_pattern(file_path: str, find: str, replace: str, regex: bool = False) -> str:
    """Replace text using pattern.
    
    Args:
        file_path: Path to file
        find: Pattern to find
        replace: Replacement text
        regex: Use regex (default False)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if regex:
            new_content = re.sub(find, replace, content, flags=re.MULTILINE)
        else:
            new_content = content.replace(find, replace)
        
        if new_content == content:
            return f"Pattern not found: {find}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return f"Replaced in {file_path}"
    except Exception as e:
        return f"Error: {e}"


@tool
def find_in_files(pattern: str, path: str = ".", file_pattern: str = "*") -> str:
    """Find pattern in all files.
    
    Args:
        pattern: Pattern to find
        path: Directory to search
        file_pattern: File pattern (e.g., "*.py")
    """
    import glob as glob_module
    
    matches = []
    
    base_path = os.path.abspath(path)
    
    for file_path in glob_module.glob(os.path.join(base_path, "**", file_pattern), recursive=True):
        if not os.path.isfile(file_path):
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if re.search(pattern, line):
                        matches.append(f"{file_path}:{i}: {line.rstrip()}")
        except Exception:
            pass
    
    if not matches:
        return f"No matches found for: {pattern}"
    
    result = f"Matches for '{pattern}' ({len(matches)} found):\n"
    return result + '\n'.join(matches[:50])


@tool
def extract_matches(file_path: str, pattern: str, group: int = 0) -> str:
    """Extract matches using regex.
    
    Args:
        file_path: Path to file
        pattern: Regex pattern
        group: Capture group to extract (0 = all)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        matches = re.findall(pattern, content)
        
        if not matches:
            return f"No matches for: {pattern}"
        
        if group > 0:
            matches = [m[group-1] if len(m) >= group else m for m in matches]
        
        return '\n'.join(matches[:20])
    except Exception as e:
        return f"Error: {e}"


@tool
def count_matches(file_path: str, pattern: str) -> str:
    """Count pattern occurrences.
    
    Args:
        file_path: Path to file
        pattern: Pattern to count
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        count = len(re.findall(pattern, content))
        
        return f"Found {count} occurrences of: {pattern}"
    except Exception as e:
        return f"Error: {e}"


__all__ = ["replace_pattern", "find_in_files", "extract_matches", "count_matches"]