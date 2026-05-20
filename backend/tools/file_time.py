import os
import asyncio
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class FileTimeState:
    read_times: Dict[str, Dict[str, datetime]] = field(default_factory=dict)
    locks: Dict[str, asyncio.Lock] = field(default_factory=dict)


class FileTime:
    _state: FileTimeState = FileTimeState()

    @classmethod
    def read(cls, session_id: str, filepath: str) -> None:
        """Record when a file was read by a session."""
        if session_id not in cls._state.read_times:
            cls._state.read_times[session_id] = {}
        cls._state.read_times[session_id][filepath] = datetime.now()

    @classmethod
    def get(cls, session_id: str, filepath: str) -> Optional[datetime]:
        """Get last read time for a file in a session."""
        return cls._state.read_times.get(session_id, {}).get(filepath)

    @classmethod
    async def with_lock(cls, filepath: str) -> asyncio.Lock:
        """Get or create a lock for a file to serialize writes."""
        if filepath not in cls._state.locks:
            cls._state.locks[filepath] = asyncio.Lock()
        return cls._state.locks[filepath]

    @classmethod
    async def assert_read(cls, session_id: str, filepath: str) -> None:
        """Assert that the file was read before editing."""
        read_time = cls.get(session_id, filepath)
        if not read_time:
            raise FileNotReadError(
                f"You must read the file {filepath} before overwriting it. Use the Read tool first"
            )

        if os.path.exists(filepath):
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime > read_time:
                raise FileModifiedError(
                    f"File {filepath} has been modified since it was last read.\n"
                    f"Last modification: {mtime.isoformat()}\n"
                    f"Last read: {read_time.isoformat()}\n\n"
                    f"Please read the file again before modifying it."
                )


class FileNotReadError(Exception):
    pass


class FileModifiedError(Exception):
    pass