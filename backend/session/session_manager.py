import os
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class SessionMessage:
    """Session message"""
    role: str
    content: str
    tool_call_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    """Agent session - manages conversation state"""
    id: str
    cwd: str
    created_at: float
    updated_at: float
    messages: List[SessionMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    model: Optional[str] = None
    agent: str = "build"


class SessionManager:
    """Session manager - manages multiple sessions"""
    
    _sessions: Dict[str, Session] = {}
    _active_session: Optional[str] = None
    
    @classmethod
    def create(cls, cwd: str = None, model: str = None, agent: str = "build") -> Session:
        """Create a new session"""
        session_id = str(uuid.uuid4())[:8]
        cwd = cwd or os.getcwd()
        
        session = Session(
            id=session_id,
            cwd=cwd,
            created_at=time.time(),
            updated_at=time.time(),
            model=model,
            agent=agent,
            messages=[]
        )
        
        cls._sessions[session_id] = session
        cls._active_session = session_id
        
        return session
    
    @classmethod
    def get(cls, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return cls._sessions.get(session_id)
    
    @classmethod
    def get_active(cls) -> Optional[Session]:
        """Get active session"""
        if cls._active_session:
            return cls._sessions.get(cls._active_session)
        
        # Create default session if none exists
        return cls.create()
    
    @classmethod
    def set_active(cls, session_id: str):
        """Set active session"""
        if session_id in cls._sessions:
            cls._active_session = session_id
    
    @classmethod
    def list(cls) -> List[Session]:
        """List all sessions"""
        return list(cls._sessions.values())
    
    @classmethod
    def add_message(cls, session_id: str, role: str, content: str, tool_call_id: str = None):
        """Add message to session"""
        session = cls._sessions.get(session_id)
        if not session:
            return
        
        message = SessionMessage(
            role=role,
            content=content,
            tool_call_id=tool_call_id
        )
        session.messages.append(message)
        session.updated_at = time.time()
    
    @classmethod
    def get_messages(cls, session_id: str, limit: int = None) -> List[SessionMessage]:
        """Get session messages"""
        session = cls._sessions.get(session_id)
        if not session:
            return []
        
        messages = session.messages
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    @classmethod
    def clear(cls, session_id: str = None):
        """Clear session"""
        if session_id:
            cls._sessions.pop(session_id, None)
        else:
            cls._sessions.clear()
            cls._active_session = None
    
    @classmethod
    def save(cls, session_id: str, filepath: str = None) -> bool:
        """Save session to file"""
        session = cls._sessions.get(session_id)
        if not session:
            return False
        
        filepath = filepath or os.path.join(session.cwd, ".opencode", "sessions", f"{session_id}.json")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = {
            "id": session.id,
            "cwd": session.cwd,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "model": session.model,
            "agent": session.agent,
            "messages": [
                {"role": m.role, "content": m.content, "tool_call_id": m.tool_call_id}
                for m in session.messages
            ]
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            return False
    
    @classmethod
    def load(cls, filepath: str) -> Optional[Session]:
        """Load session from file"""
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            session = Session(
                id=data.get("id", ""),
                cwd=data.get("cwd", ""),
                created_at=data.get("created_at", time.time()),
                updated_at=data.get("updated_at", time.time()),
                model=data.get("model"),
                agent=data.get("agent", "build")
            )
            
            for msg in data.get("messages", []):
                session.messages.append(SessionMessage(
                    role=msg.get("role", ""),
                    content=msg.get("content", ""),
                    tool_call_id=msg.get("tool_call_id")
                ))
            
            cls._sessions[session.id] = session
            return session
        except Exception:
            return None


__all__ = ["Session", "SessionMessage", "SessionManager"]