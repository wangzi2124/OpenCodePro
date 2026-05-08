import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools import tool_registry
registry = tool_registry


def glob_search(pattern: str, path: str = "."):
    """Fast file pattern matching tool. Supports glob patterns like "**/*.js" or "src/**/*.ts". Returns matching file paths sorted by modification time."""
    try:
        search_base = path if path != "." else os.getcwd()
        full_pattern = os.path.join(search_base, pattern) if not os.path.isabs(pattern) else pattern
        files = glob.glob(full_pattern, recursive=True)
        
        files_with_mtime = []
        for f in files:
            try:
                mtime = os.path.getmtime(f)
                files_with_mtime.append((mtime, f))
            except:
                pass
        
        files_with_mtime.sort(key=lambda x: x[0])
        sorted_files = [f for _, f in files_with_mtime]
        
        return {"files": sorted_files[:500], "count": len(sorted_files)}
    except Exception as e:
        return {"error": str(e)}


registry.register(glob_search)


def grep_search(pattern: str, include: str = "*", path: str = "."):
    """Fast content search tool using regular expressions. Supports full regex syntax (eg "log.*Error", "function\\s+\\w+", etc). Filter files by pattern with include parameter (eg "*.js", "*.{ts,tsx}"). Returns file paths and line numbers with at least one match sorted by modification time."""
    try:
        search_path = path if os.path.isabs(path) else os.path.abspath(path)

        include_pattern = include if include != "*" else "**/*"
        file_pattern = os.path.join(search_path, include_pattern)
        files = glob.glob(file_pattern, recursive=True)

        results = []
        regex = re.compile(pattern)
        
        for file_path in files[:200]:
            if os.path.isfile(file_path):
                matches = []
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                rel_path = os.path.relpath(file_path, search_path)
                                matches.append(f"{rel_path}:{line_num}: {line.rstrip()}")
                                if len(matches) >= 10:
                                    break
                except Exception:
                    pass
                
                if matches:
                    results.append({"file": file_path, "matches": matches[:10]})

        return {"results": results, "total_matches": len(results)}
    except Exception as e:
        return {"error": str(e)}


registry.register(grep_search)
