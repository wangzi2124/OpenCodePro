import os
import subprocess
import asyncio
import platform
from typing import Optional, AsyncGenerator
from pathlib import Path


class Ripgrep:
    _rg_path: Optional[str] = None
    _initialized: bool = False

    @classmethod
    async def find_rg(cls) -> str:
        """Find ripgrep executable, downloading if needed."""
        if cls._rg_path:
            return cls._rg_path

        # Check if rg is in PATH
        rg_name = "rg.exe" if platform.system() == "Windows" else "rg"
        for path in os.environ.get("PATH", "").split(os.pathsep):
            full_path = os.path.join(path, rg_name)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                cls._rg_path = full_path
                return cls._rg_path

        # Try common Windows locations
        if platform.system() == "Windows":
            common_paths = [
                r"C:\Program Files\ripgrep-14.1.1\rg.exe",
                r"C:\Program Files (x86)\ripgrep-14.1.1\rg.exe",
            ]
            for p in common_paths:
                if os.path.isfile(p):
                    cls._rg_path = p
                    return cls._rg_path

        # Fallback to simple grep on Windows
        if platform.system() == "Windows":
            return "findstr"

        return "rg"

    @classmethod
    async def filepath(cls) -> str:
        """Get ripgrep filepath."""
        return await cls.find_rg()

    @classmethod
    async def files(cls, cwd: str, glob: list = None) -> AsyncGenerator[str, None]:
        """List files in directory using ripgrep."""
        rg_path = await cls.filepath()

        if rg_path == "findstr":
            # Windows fallback - use findstr
            proc = await asyncio.create_subprocess_exec(
                "cmd", "/c", "dir", "/s", "/b", cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            for line in stdout.decode("utf-8", errors="ignore").split("\n"):
                line = line.strip()
                if line and not line.endswith("\\$RECYCLE.BIN"):
                    yield line
            return

        args = [rg_path, "--files", "--follow", "--hidden", "--glob=!.git/*"]
        if glob:
            for g in glob:
                args.append(f"--glob={g}")

        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, _ = await proc.communicate()
        for line in stdout.decode("utf-8", errors="ignore").split("\n"):
            line = line.strip()
            if line:
                yield os.path.join(cwd, line)

    @classmethod
    async def search(
        cls,
        cwd: str,
        pattern: str,
        glob: str = None,
        limit: int = 100
    ) -> list:
        """Search files using ripgrep."""
        rg_path = await cls.filepath()

        if rg_path == "findstr":
            return await cls._search_fallback(cwd, pattern, glob, limit)

        args = [
            rg_path, "-nH", "--field-match-separator=|",
            "--regexp", pattern,
            "--max-count", str(limit)
        ]
        if glob:
            args.extend(["--glob", glob])
        args.extend(["--glob=!.git/*"])
        args.append(cwd)

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 1:
                return []

            output = stdout.decode("utf-8", errors="ignore")
            results = []

            for line in output.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) >= 3:
                    results.append({
                        "path": parts[0],
                        "line_num": int(parts[1]),
                        "line_text": "|".join(parts[2:])
                    })

            return results

        except Exception as e:
            return []

    @classmethod
    async def _search_fallback(cls, cwd: str, pattern: str, glob: str, limit: int) -> list:
        """Fallback search using Python when ripgrep unavailable."""
        import re
        results = []
        count = 0

        try:
            async for filepath in cls.files(cwd, [glob] if glob else None):
                if count >= limit:
                    break

                if glob and not re.match(glob.replace("*", ".*"), os.path.basename(filepath)):
                    continue

                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f):
                            if re.search(pattern, line):
                                results.append({
                                    "path": filepath,
                                    "line_num": i + 1,
                                    "line_text": line.rstrip()
                                })
                                count += 1
                                if count >= limit:
                                    break
                except:
                    continue

        except Exception:
            pass

        return results

    @classmethod
    async def tree(cls, cwd: str, limit: int = 50) -> str:
        """Get directory tree structure."""
        files = []
        async for f in cls.files(cwd):
            rel = os.path.relpath(f, cwd)
            if ".opencode" not in rel:
                files.append(rel)

        files.sort()

        # Build tree
        tree = {}
        for f in files:
            parts = f.split(os.sep)
            current = tree
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]

        def render(node, prefix="", is_last=True):
            lines = []
            items = list(node.items())
            for i, (name, children) in enumerate(items):
                is_last_item = i == len(items) - 1
                connector = "└── " if is_last_item else "├── "
                lines.append(prefix + connector + name)
                if children:
                    extension = "    " if is_last_item else "│   "
                    lines.extend(render(children, prefix + extension, is_last_item))
            return lines

        result = render(tree)
        return "\n".join(result[:limit])


class Glob:
    """Fast glob using ripgrep."""

    @classmethod
    async def search(cls, pattern: str, cwd: str = ".") -> list:
        """Search files matching glob pattern."""
        import fnmatch

        results = []
        limit = 100
        count = 0

        async for filepath in Ripgrep.files(cwd):
            if count >= limit:
                break
            if fnmatch.fnmatch(os.path.basename(filepath), pattern):
                results.append(filepath)
                count += 1

        return results