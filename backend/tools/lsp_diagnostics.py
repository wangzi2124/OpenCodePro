import os
import asyncio
import subprocess
from typing import Dict, List, Optional


class LSPDiagnostics:
    """Simple LSP diagnostics using common tools."""

    @staticmethod
    def get_language_server(filepath: str) -> Optional[str]:
        """Get appropriate language server for file type."""
        ext = os.path.splitext(filepath)[1].lower()
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".vue": "vue",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
        }
        return lang_map.get(ext)

    @staticmethod
    async def diagnose(filepath: str) -> List[Dict]:
        """Get diagnostics for a file."""
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".py":
            return await LSPDiagnostics._diagnose_python(filepath)
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            return await LSPDiagnostics._diagnose_js(filepath)
        elif ext == ".json":
            return await LSPDiagnostics._diagnose_json(filepath)

        return []

    @staticmethod
    async def _diagnose_python(filepath: str) -> List[Dict]:
        """Diagnose Python file using pyright or basic checks."""
        try:
            result = await asyncio.create_subprocess_exec(
                "pyright", filepath, "--outputjson",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode == 0:
                import json
                data = json.loads(stdout.decode("utf-8"))
                diagnostics = []

                for diag in data.get("generalDiagnostics", []):
                    diagnostics.append({
                        "line": diag.get("range", {}).get("start", {}).get("line", 0),
                        "message": diag.get("message", ""),
                        "severity": diag.get("severity", 1),
                    })

                return diagnostics
        except FileNotFoundError:
            pass

        return await LSPDiagnostics._diagnose_python_fallback(filepath)

    @staticmethod
    async def _diagnose_python_fallback(filepath: str) -> List[Dict]:
        """Fallback using Python compile check."""
        try:
            result = await asyncio.create_subprocess_exec(
                "python", "-m", "py_compile", filepath,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                error = stderr.decode("utf-8")
                lines = error.split("\n")
                diagnostics = []

                for line in lines:
                    if "SyntaxError" in line or "IndentationError" in line:
                        import re
                        match = re.search(r"line (\d+)", line)
                        line_num = int(match.group(1)) - 1 if match else 0
                        diagnostics.append({
                            "line": line_num,
                            "message": line,
                            "severity": 1,
                        })

                return diagnostics
        except:
            pass

        return []

    @staticmethod
    async def _diagnose_js(filepath: str) -> List[Dict]:
        """Diagnose JavaScript/TypeScript file."""
        try:
            result = await asyncio.create_subprocess_exec(
                "npx", "eslint", filepath, "--format=json",
                cwd=os.path.dirname(filepath) or ".",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await result.communicate()

            if result.returncode in [0, 1]:
                import json
                try:
                    data = json.loads(stdout.decode("utf-8"))
                    diagnostics = []

                    for file_data in data:
                        for msg in file_data.get("messages", []):
                            diagnostics.append({
                                "line": msg.get("line", 0) - 1,
                                "message": f"{msg.get('message')} (rule: {msg.get('ruleId', 'unknown')})",
                                "severity": 2 if msg.get("severity", 1) == 1 else 1,
                            })

                    return diagnostics
                except:
                    pass
        except:
            pass

        return []

    @staticmethod
    async def _diagnose_json(filepath: str) -> List[Dict]:
        """Diagnose JSON file."""
        try:
            import json
            with open(filepath, "r") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            return [{
                "line": e.lineno - 1 if e.lineno else 0,
                "message": str(e),
                "severity": 1,
            }]
        except:
            pass

        return []

    @staticmethod
    def format_diagnostics(diagnostics: List[Dict], max_per_file: int = 20) -> str:
        """Format diagnostics for output."""
        if not diagnostics:
            return ""

        output = "<file_diagnostics>\n"
        limited = diagnostics[:max_per_file]

        for diag in limited:
            severity = "ERROR" if diag.get("severity", 1) == 1 else "WARNING"
            line = diag.get("line", 0) + 1
            output += f"  Line {line}: [{severity}] {diag.get('message', '')}\n"

        if len(diagnostics) > max_per_file:
            output += f"  ... and {len(diagnostics) - max_per_file} more\n"

        output += "</file_diagnostics>"
        return output


async def get_diagnostics_after_edit(filepath: str) -> str:
    """Get diagnostics after editing a file."""
    diagnostics = await LSPDiagnostics.diagnose(filepath)
    return LSPDiagnostics.format_diagnostics(diagnostics)