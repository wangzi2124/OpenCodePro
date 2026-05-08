import os
import subprocess
import sys
import inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tools import tool_registry
registry = tool_registry


def run_bash(command: str, workdir: str = None, timeout: int = 120):
    """Execute a bash/terminal command and return stdout/stderr"""
    try:
        cwd = workdir if workdir else os.getcwd()
        is_win = sys.platform == "win32"

        shell = "powershell.exe" if is_win else "/bin/bash"

        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "stdout": result.stdout or "(no output)",
            "stderr": result.stderr or "",
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out ({timeout}s)", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


registry.register(run_bash)
