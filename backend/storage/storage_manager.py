import os
import json
import sqlite3
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import threading


class StorageType(str, Enum):
    MEMORY = "memory"
    FILE = "file"
    SQLITE = "sqlite"


@dataclass
class StorageRecord:
    """Storage record"""
    id: str
    data: Dict
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class StorageManager:
    """Storage manager - handles persistent data"""
    
    _db_path: str = None
    _memory_store: Dict[str, StorageRecord] = {}
    _lock = threading.Lock()
    _local = threading.local()
    
    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        """Get thread-local connection"""
        if not hasattr(cls._local, 'connection') or cls._local.connection is None:
            cls._local.connection = sqlite3.connect(cls._db_path)
            cls._local.connection.row_factory = sqlite3.Row
        return cls._local.connection
    
    @classmethod
    def initialize(cls, db_path: str = None):
        """Initialize storage"""
        cls._db_path = db_path or os.path.join(os.getcwd(), ".opencode", "storage.db")
        
        os.makedirs(os.path.dirname(cls._db_path), exist_ok=True)
        
        cls._create_tables()
    
    @classmethod
    def _create_tables(cls):
        """Create tables"""
        conn = cls._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                data TEXT,
                created_at REAL,
                updated_at REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                data TEXT,
                created_at REAL,
                updated_at REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp REAL
            )
        """)
        
        conn.commit()
    
    @classmethod
    def set(cls, key: str, data: Any):
        """Set record"""
        record = StorageRecord(
            id=key,
            data=data if isinstance(data, dict) else {"value": data}
        )
        
        with cls._lock:
            cls._memory_store[key] = record
        
        if cls._db_path:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO records (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (key, json.dumps(record.data), record.created_at, record.updated_at)
            )
            conn.commit()
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get record"""
        with cls._lock:
            record = cls._memory_store.get(key)
        
        if record:
            return record.data
        
        if cls._db_path:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM records WHERE id = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        
        return default
    
    @classmethod
    def delete(cls, key: str):
        """Delete record"""
        with cls._lock:
            cls._memory_store.pop(key, None)
        
        if cls._db_path:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM records WHERE id = ?", (key,))
            conn.commit()
    
    @classmethod
    def list(cls, prefix: str = None) -> List[str]:
        """List keys"""
        with cls._lock:
            keys = list(cls._memory_store.keys())
        
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        
        return keys
    
    @classmethod
    def save_session(cls, session_id: str, messages: List[Dict]):
        """Save session"""
        data = {"id": session_id, "messages": messages}
        
        cls.set(f"session:{session_id}", data)
        
        if cls._db_path:
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO sessions (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, json.dumps(data), time.time(), time.time())
            )
            conn.commit()
    
    @classmethod
    def load_session(cls, session_id: str) -> Optional[Dict]:
        """Load session"""
        return cls.get(f"session:{session_id}")
    
    @classmethod
    def close(cls):
        """Close storage"""
        if hasattr(cls._local, 'connection') and cls._local.connection:
            cls._local.connection.close()
            cls._local.connection = None


class CacheManager:
    """Cache manager"""
    
    _cache: Dict[str, Dict] = {}
    _max_size: int = 100
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Get from cache"""
        entry = cls._cache.get(key)
        
        if not entry:
            return None
        
        if time.time() - entry["timestamp"] > entry.get("ttl", 3600):
            cls._cache.pop(key, None)
            return None
        
        return entry["value"]
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: int = 3600):
        """Set cache"""
        if len(cls._cache) >= cls._max_size:
            oldest = min(cls._cache.items(), key=lambda x: x[1]["timestamp"])
            cls._cache.pop(oldest[0], None)
        
        cls._cache[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl
        }
    
    @classmethod
    def clear(cls):
        """Clear cache"""
        cls._cache.clear()


__all__ = ["StorageManager", "CacheManager", "StorageRecord", "StorageType"]