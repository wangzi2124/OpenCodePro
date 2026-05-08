import os
import time
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
from threading import Thread, Lock
import fnmatch


class FileEventType(str, Enum):
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileEvent:
    """File system event"""
    path: str
    event_type: FileEventType
    timestamp: float = field(default_factory=time.time)


class FileWatcher:
    """File watcher - monitors file system changes"""
    
    _watchers: Dict[str, 'FileWatcher'] = {}
    _running: bool = False
    _callbacks: List[Callable] = []
    _ignore_patterns: List[str] = [
        "__pycache__",
        "*.pyc",
        ".git",
        "node_modules",
        ".venv",
        "*.log",
    ]
    
    @classmethod
    def watch(cls, directory: str, callback: Callable = None, ignore_patterns: List[str] = None):
        """Watch directory for changes"""
        directory = os.path.abspath(directory)
        
        if directory in cls._watchers:
            return cls._watchers[directory]
        
        if ignore_patterns:
            cls._ignore_patterns = ignore_patterns
        
        watcher = FileWatcher(directory)
        cls._watchers[directory] = watcher
        
        if callback:
            cls._callbacks.append(callback)
        
        return watcher
    
    @classmethod
    def start(cls):
        """Start watching"""
        cls._running = True
        
        for watcher in cls._watchers.values():
            thread = Thread(target=watcher._run)
            thread.daemon = True
            thread.start()
    
    @classmethod
    def stop(cls):
        """Stop watching"""
        cls._running = False
    
    @classmethod
    def on_change(cls, callback: Callable):
        """Register change callback"""
        cls._callbacks.append(callback)
    
    def __init__(self, directory: str):
        self.directory = directory
        self._last_mtimes: Dict[str, float] = {}
        self._events: List[FileEvent] = []
    
    def _run(self):
        """Run watcher loop"""
        while FileWatcher._running:
            try:
                self._check_changes()
            except Exception:
                pass
            time.sleep(1)
    
    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored"""
        for pattern in self._ignore_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        
        parts = path.split(os.sep)
        for part in parts:
            if part.startswith('.') or part in self._ignore_patterns:
                return True
        
        return False
    
    def _check_changes(self):
        """Check for file changes"""
        events = []
        
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if not self._should_ignore(d)]
            
            for filename in files:
                if self._should_ignore(filename):
                    continue
                
                path = os.path.join(root, filename)
                
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    continue
                
                last_mtime = self._last_mtimes.get(path, 0)
                
                if mtime > last_mtime:
                    if last_mtime == 0:
                        event_type = FileEventType.CREATED
                    else:
                        event_type = FileEventType.MODIFIED
                    
                    events.append(FileEvent(path, event_type))
                    self._last_mtimes[path] = mtime
        
        # Check for deleted files
        for path in list(self._last_mtimes.keys()):
            if not os.path.exists(path):
                events.append(FileEvent(path, FileEventType.DELETED))
                self._last_mtimes.pop(path, None)
        
        # Notify callbacks
        if events:
            for callback in FileWatcher._callbacks:
                try:
                    callback(events)
                except Exception:
                    pass


# Standalone functions for tools

def watch_directory(directory: str, patterns: List[str] = None) -> str:
    """Start watching directory for changes"""
    try:
        FileWatcher.watch(directory, ignore_patterns=patterns)
        return f"Watching {directory}"
    except Exception as e:
        return f"Error: {e}"


def get_changes(directory: str) -> List[FileEvent]:
    """Get recent file changes"""
    watcher = FileWatcher._watchers.get(directory)
    if watcher:
        return watcher._events
    return []


__all__ = ["FileWatcher", "FileEvent", "FileEventType"]