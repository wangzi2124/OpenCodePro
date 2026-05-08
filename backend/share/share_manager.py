import os
import json
import uuid
import time
import base64
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ShareLink:
    """Share link"""
    id: str
    session_id: str
    created_at: float
    expires_at: Optional[float] = None
    password: Optional[str] = None
    view_count: int = 0


class ShareManager:
    """Share manager - create shareable links"""
    
    _links: Dict[str, ShareLink] = {}
    
    @classmethod
    def create_link(cls, session_id: str, expires_in: int = None, password: str = None) -> str:
        """Create share link"""
        link_id = secrets.token_urlsafe(8)
        
        expires_at = None
        if expires_in:
            expires_at = time.time() + expires_in
        
        link = ShareLink(
            id=link_id,
            session_id=session_id,
            expires_at=expires_at,
            password=password
        )
        
        cls._links[link_id] = link
        
        return link_id
    
    @classmethod
    def get_link(cls, link_id: str) -> Optional[ShareLink]:
        """Get share link"""
        return cls._links.get(link_id)
    
    @classmethod
    def is_valid(cls, link_id: str) -> bool:
        """Check if link is valid"""
        link = cls._links.get(link_id)
        
        if not link:
            return False
        
        if link.expires_at and time.time() > link.expires_at:
            return False
        
        link.view_count += 1
        return True
    
    @classmethod
    def verify_password(cls, link_id: str, password: str) -> bool:
        """Verify link password"""
        from backend.auth.auth_manager import AuthManager
        
        link = cls._links.get(link_id)
        
        if not link:
            return False
        
        if not link.password:
            return True
        
        return AuthManager.verify_password(password, link.password)
    
    @classmethod
    def export_encoded(cls, session_data: Dict, password: str = None) -> str:
        """Export session as encoded string"""
        data = json.dumps(session_data)
        
        if password:
            from backend.auth.auth_manager import AuthManager
            hashed = AuthManager.hash_password(password)
            encoded = base64.b64encode(data.encode()).decode()
            return f"oc://{len(hashed)}:{hashed}:{encoded}"
        
        encoded = base64.b64encode(data.encode()).decode()
        return f"oc::{encoded}"
    
    @classmethod
    def import_encoded(cls, encoded: str) -> Optional[Dict]:
        """Import from encoded string"""
        if not encoded.startswith("oc::") and not encoded.startswith("oc:"):
            return None
        
        parts = encoded[3:].split(":", 1)
        
        if len(parts) == 2 and parts[0].isdigit():
            # Password protected
            return None
        
        try:
            data = base64.b64decode(parts[-1]).decode()
            return json.loads(data)
        except Exception:
            return None
    
    @classmethod
    def delete_link(cls, link_id: str):
        """Delete link"""
        cls._links.pop(link_id, None)


import secrets  # Add missing import


__all__ = ["ShareManager", "ShareLink"]