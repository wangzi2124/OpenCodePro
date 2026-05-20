import os
import json
import time
import hashlib
import difflib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from backend.storage.storage_manager import StorageManager


@dataclass
class FileSnapshot:
    path: str
    content_hash: str
    content: str
    timestamp: float
    size: int


@dataclass
class SnapshotDiff:
    path: str
    added_lines: List[str] = field(default_factory=list)
    removed_lines: List[str] = field(default_factory=list)
    modified: bool = False


class SnapshotManager:
    """Tracks file state changes during a session."""

    _snapshots: Dict[str, FileSnapshot] = {}
    _session_snapshots: Dict[str, Dict[str, FileSnapshot]] = {}

    @classmethod
    def take_snapshot(cls, file_path: str, session_id: str = "default") -> FileSnapshot:
        """Take a snapshot of a file's current state."""
        abs_path = os.path.abspath(file_path) if not os.path.isabs(file_path) else file_path

        if not os.path.exists(abs_path):
            return None

        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        snapshot = FileSnapshot(
            path=abs_path,
            content_hash=content_hash,
            content=content,
            timestamp=time.time(),
            size=len(content),
        )

        cls._snapshots[abs_path] = snapshot

        if session_id not in cls._session_snapshots:
            cls._session_snapshots[session_id] = {}
        cls._session_snapshots[session_id][abs_path] = snapshot

        # Persist
        StorageManager.set(f"snapshot:{session_id}:{abs_path.replace(os.sep, '/')}", {
            "path": abs_path,
            "content_hash": content_hash,
            "content": content,
            "timestamp": snapshot.timestamp,
            "size": snapshot.size,
        })

        return snapshot

    @classmethod
    def diff_snapshot(cls, file_path: str, session_id: str = "default") -> Optional[SnapshotDiff]:
        """Compare current file state against snapshot."""
        abs_path = os.path.abspath(file_path) if not os.path.isabs(file_path) else file_path

        snapshot = None
        if abs_path in cls._snapshots:
            snapshot = cls._snapshots[abs_path]
        elif session_id in cls._session_snapshots and abs_path in cls._session_snapshots[session_id]:
            snapshot = cls._session_snapshots[session_id][abs_path]

        if not snapshot:
            stored = StorageManager.get(f"snapshot:{session_id}:{abs_path.replace(os.sep, '/')}")
            if stored:
                snapshot = FileSnapshot(**stored)
                cls._snapshots[abs_path] = snapshot

        if not snapshot:
            return SnapshotDiff(path=abs_path, modified=False)

        if not os.path.exists(abs_path):
            return SnapshotDiff(
                path=abs_path,
                removed_lines=snapshot.content.splitlines(),
                modified=True,
            )

        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            current_content = f.read()

        current_hash = hashlib.sha256(current_content.encode()).hexdigest()[:16]
        if current_hash == snapshot.content_hash:
            return SnapshotDiff(path=abs_path, modified=False)

        old_lines = snapshot.content.splitlines()
        new_lines = current_content.splitlines()
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))

        added = [l[2:] for l in diff if l.startswith("+") and not l.startswith("+++")]
        removed = [l[2:] for l in diff if l.startswith("-") and not l.startswith("---")]

        return SnapshotDiff(path=abs_path, added_lines=added, removed_lines=removed, modified=True)

    @classmethod
    def get_changed_files(cls, session_id: str = "default") -> List[SnapshotDiff]:
        """Get all files changed since session snapshots were taken."""
        changed = []
        snapshots = cls._session_snapshots.get(session_id, {})

        for abs_path in list(snapshots.keys()):
            diff = cls.diff_snapshot(abs_path, session_id)
            if diff and diff.modified:
                changed.append(diff)

        return changed

    @classmethod
    def revert_file(cls, file_path: str, session_id: str = "default") -> bool:
        """Revert a file to its snapshot state."""
        abs_path = os.path.abspath(file_path) if not os.path.isabs(file_path) else file_path

        snapshot = None
        if abs_path in cls._snapshots:
            snapshot = cls._snapshots[abs_path]
        elif session_id in cls._session_snapshots and abs_path in cls._session_snapshots[session_id]:
            snapshot = cls._session_snapshots[session_id][abs_path]

        if not snapshot:
            return False

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(snapshot.content)
        return True

    @classmethod
    def clear_session(cls, session_id: str):
        """Clear all snapshots for a session."""
        if session_id in cls._session_snapshots:
            cls._session_snapshots[session_id].clear()
        StorageManager.delete(f"snapshot:{session_id}")

    @classmethod
    def list_session_snapshots(cls, session_id: str) -> List[str]:
        """List all files snapshotted in a session."""
        snapshots = cls._session_snapshots.get(session_id, {})
        return [os.path.relpath(p, os.getcwd()) for p in snapshots.keys()]


__all__ = [
    "SnapshotManager",
    "FileSnapshot",
    "SnapshotDiff",
]