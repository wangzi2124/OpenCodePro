import os
from pathlib import Path
from typing import Optional


class Filesystem:
    @staticmethod
    def contains(parent: str, child: str) -> bool:
        """Check if child path is within parent directory."""
        try:
            rel = os.path.relpath(child, parent)
            return not rel.startswith("..") and not os.path.isabs(rel)
        except ValueError:
            return False

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize path for cross-platform compatibility."""
        return os.path.normpath(os.path.abspath(path))

    @staticmethod
    async def find_up(target: str, start: str, stop: Optional[str] = None) -> list:
        """Search upward from start directory for target file."""
        results = []
        current = start

        while True:
            search = os.path.join(current, target)
            if os.path.exists(search):
                results.append(search)
            if stop and current == stop:
                break
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

        return results


def is_binary_file(filepath: str) -> bool:
    """Check if file is binary."""
    ext = os.path.splitext(filepath)[1].lower()
    binary_exts = {
        ".zip", ".tar", ".gz", ".exe", ".dll", ".so", ".class", ".jar", ".war",
        ".7z", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt",
        ".ods", ".odp", ".bin", ".dat", ".obj", ".o", ".a", ".lib",
        ".wasm", ".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".bmp",
        ".ico", ".svg", ".pdf", ".mp3", ".mp4", ".wav", ".avi", ".mov"
    }

    if ext in binary_exts:
        return True

    # Check content
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(4096)
            if not chunk:
                return False

            non_printable = sum(1 for b in chunk if b == 0 or (b < 9 or (b > 13 and b < 32)))
            return non_printable / len(chunk) > 0.3
    except:
        return False


def get_file_type(filepath: str) -> str:
    """Get MIME type of file."""
    ext = os.path.splitext(filepath)[1].lower()
    mime_types = {
        ".txt": "text/plain",
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".xml": "application/xml",
        ".py": "text/x-python",
        ".ts": "text/typescript",
        ".tsx": "text/typescript",
        ".jsx": "text/javascript",
        ".md": "text/markdown",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".pdf": "application/pdf",
    }
    return mime_types.get(ext, "application/octet-stream")