import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError

from tools import tool_registry
registry = tool_registry


def fetch_url(url: str):
    """Fetch web page content from a URL"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8", errors="replace")
            return {"content": content[:50000]}
    except HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"error": str(e.reason)}
    except Exception as e:
        return {"error": str(e)}


registry.register(fetch_url)


def web_search(query: str):
    """Search the web for information (placeholder - use fetch tool instead)"""
    return {"message": "Web search not implemented. Use fetch tool instead."}


registry.register(web_search)


def code_search(query: str, language: str = None):
    """Search for programming code examples and patterns (placeholder)"""
    return {"message": "Code search not implemented. Use fetch tool instead."}


registry.register(code_search)
