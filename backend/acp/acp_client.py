import os
import json
import uuid
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from dataclasses_json import dataclass_json
import requests


from backend.session.session_manager import SessionManager, Session


class ACPError(Exception):
    """ACP Error"""
    pass


class ACPStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
@dataclass_json
class ACPMessage:
    """ACP message"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "message"
    role: str = "user"
    content: str = ""
    tool_calls: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
@dataclass_json
class ACPRequest:
    """ACP request"""
    session_id: str
    message: ACPMessage
    model: str = "qwen2.5:latest"
    provider: str = "ollama"
    stream: bool = True


@dataclass
@dataclass_json
class ACPResponse:
    """ACP response"""
    message: ACPMessage
    status: str = "done"
    metadata: Dict = field(default_factory=dict)


class ACPClient:
    """Agent Client Protocol - handles communication between client and server"""
    
    _server_url: str = "http://localhost:3001"
    _session_id: Optional[str] = None
    _connected: bool = False
    _message_handler: Optional[Callable] = None
    
    @classmethod
    def connect(cls, server_url: str = None) -> bool:
        """Connect to ACP server"""
        cls._server_url = server_url or cls._server_url
        
        try:
            response = requests.get(f"{cls._server_url}/api/health", timeout=5)
            cls._connected = response.status_code == 200
            return cls._connected
        except Exception:
            cls._connected = False
            return False
    
    @classmethod
    def disconnect(cls):
        """Disconnect from server"""
        cls._connected = False
        cls._session_id = None
    
    @classmethod
    def is_connected(cls) -> bool:
        """Check connection status"""
        return cls._connected
    
    @classmethod
    def create_session(cls, cwd: str = None) -> str:
        """Create new session"""
        session = SessionManager.create(cwd or os.getcwd())
        cls._session_id = session.id
        return session.id
    
    @classmethod
    def send_message(cls, content: str, stream: bool = True) -> str:
        """Send message to agent"""
        if not cls._session_id:
            cls.create_session()
        
        message = ACPMessage(
            role="user",
            content=content
        )
        
        request = ACPRequest(
            session_id=cls._session_id,
            message=message,
            stream=stream
        )
        
        try:
            response = requests.post(
                f"{cls._server_url}/api/agent/run",
                json={
                    "query": content,
                    "model": request.model,
                    "stream": stream
                },
                stream=stream,
                timeout=120
            )
            
            if stream:
                return cls._handle_stream(response)
            else:
                return response.text
        except Exception as e:
            raise ACPError(f"Failed to send message: {e}")
    
    @classmethod
    def _handle_stream(cls, response) -> str:
        """Handle streaming response"""
        content = []
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])
                
                if cls._message_handler:
                    cls._message_handler(data)
                
                if data.get('type') == 'final_answer':
                    content.append(data.get('data', ''))
        
        return '\n'.join(content)
    
    @classmethod
    def on_message(cls, handler: Callable):
        """Set message handler"""
        cls._message_handler = handler
    
    @classmethod
    def get_history(cls, limit: int = 10) -> List[Dict]:
        """Get session history"""
        if not cls._session_id:
            return []
        
        session = SessionManager.get(cls._session_id)
        if not session:
            return []
        
        return [
            {"role": m.role, "content": m.content}
            for m in session.messages[-limit:]
        ]
    
    @classmethod
    def export_session(cls) -> str:
        """Export session as JSON"""
        if not cls._session_id:
            return ""
        
        session = SessionManager.get(cls._session_id)
        if not session:
            return ""
        
        return json.dumps({
            "id": session.id,
            "cwd": session.cwd,
            "created_at": session.created_at,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in session.messages
            ]
        }, indent=2)


class ACPServer:
    """ACP Server implementation"""
    
    _sessions: Dict[str, Dict] = {}
    
    @classmethod
    def create_session(cls, cwd: str) -> str:
        """Create session"""
        session_id = str(uuid.uuid4())[:8]
        
        cls._sessions[session_id] = {
            "id": session_id,
            "cwd": cwd,
            "created_at": time.time(),
            "messages": []
        }
        
        return session_id
    
    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict]:
        """Get session"""
        return cls._sessions.get(session_id)
    
    @classmethod
    def add_message(cls, session_id: str, role: str, content: str):
        """Add message to session"""
        session = cls._sessions.get(session_id)
        if session:
            session["messages"].append({
                "role": role,
                "content": content,
                "timestamp": time.time()
            })
    
    @classmethod
    def delete_session(cls, session_id: str):
        """Delete session"""
        cls._sessions.pop(session_id, None)


__all__ = ["ACPClient", "ACPServer", "ACPMessage", "ACPRequest", "ACPResponse", "ACPError", "ACPStatus"]