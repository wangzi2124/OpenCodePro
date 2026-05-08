import os
import json
import time
import hashlib
import secrets
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class AuthProvider(str, Enum):
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    ANONYMOUS = "anonymous"


class AuthError(Exception):
    pass


@dataclass
class User:
    """User"""
    id: str
    name: str
    email: Optional[str] = None
    provider: AuthProvider = AuthProvider.NONE
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class AuthToken:
    """Auth token"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class AuthManager:
    """Auth manager"""
    
    _users: Dict[str, User] = {}
    _tokens: Dict[str, Dict] = {}
    _current_user: Optional[User] = None
    
    @classmethod
    def hash_password(cls, password: str, salt: str = None) -> str:
        """Hash password"""
        salt = salt or secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{hash_obj.hex()}"
    
    @classmethod
    def verify_password(cls, password: str, hashed: str) -> bool:
        """Verify password"""
        try:
            salt, hash_hex = hashed.split(':')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hash_obj.hex() == hash_hex
        except Exception:
            return False
    
    @classmethod
    def create_user(cls, name: str, email: str = None, password: str = None) -> User:
        """Create user"""
        user_id = secrets.token_hex(8)
        
        user = User(
            id=user_id,
            name=name,
            email=email,
            provider=AuthProvider.API_KEY if password else AuthProvider.NONE
        )
        
        cls._users[user_id] = user
        cls._current_user = user
        
        return user
    
    @classmethod
    def authenticate(cls, email: str, password: str) -> Optional[AuthToken]:
        """Authenticate user"""
        user = next((u for u in cls._users.values() if u.email == email), None)
        
        if not user:
            raise AuthError("User not found")
        
        if not cls.verify_password(password, user.metadata.get("password", "")):
            raise AuthError("Invalid password")
        
        access_token = secrets.token_urlsafe(32)
        
        token = AuthToken(
            access_token=access_token,
            refresh_token=secrets.token_urlsafe(32)
        )
        
        cls._tokens[access_token] = {
            "user_id": user.id,
            "created_at": time.time()
        }
        
        return token
    
    @classmethod
    def get_current_user(cls) -> Optional[User]:
        """Get current user"""
        return cls._current_user
    
    @classmethod
    def set_current_user(cls, user_id: str):
        """Set current user"""
        cls._current_user = cls._users.get(user_id)
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[User]:
        """Verify token"""
        token_data = cls._tokens.get(token)
        
        if not token_data:
            return None
        
        if time.time() - token_data["created_at"] > 3600:
            return None
        
        return cls._users.get(token_data["user_id"])
    
    @classmethod
    def logout(cls):
        """Logout"""
        cls._current_user = None
        cls._tokens.clear()


class OAuthManager:
    """OAuth manager for external providers"""
    
    _providers: Dict[str, Dict] = {
        "openai": {
            "auth_url": "https://chat.openai.com",
            "token_url": "https://api.openai.com/v1/oauth/token",
        },
        "anthropic": {
            "auth_url": "https://auth.anthropic.com",
            "token_url": "https://api.anthropic.com/oauth/token",
        },
        "google": {
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
        },
    }
    
    @classmethod
    def get_auth_url(cls, provider: str, client_id: str, redirect_uri: str) -> str:
        """Get OAuth URL"""
        provider_config = cls._providers.get(provider, {})
        
        if not provider_config:
            raise AuthError(f"Unknown provider: {provider}")
        
        return f"{provider_config['auth_url']}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"
    
    @classmethod
    def exchange_code(cls, provider: str, code: str, client_id: str, client_secret: str) -> Optional[AuthToken]:
        """Exchange code for token"""
        provider_config = cls._providers.get(provider, {})
        
        if not provider_config:
            return None
        
        # In real implementation, would call token endpoint
        return AuthToken(
            access_token=secrets.token_urlsafe(32),
            token_type="Bearer"
        )


__all__ = ["AuthManager", "OAuthManager", "User", "AuthToken", "AuthProvider", "AuthError"]