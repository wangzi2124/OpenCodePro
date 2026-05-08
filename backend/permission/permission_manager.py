import os
import re
import json
import hashlib
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock


class DangerLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


DANGEROUS_PATTERNS = {
    # File destruction
    r"rm\s+-rf": (DangerLevel.CRITICAL, "删除整个目录树"),
    r"del\s+/[sq]": (DangerLevel.CRITICAL, "Windows 删除文件"),
    r"rmdir\s+/[s]": (DangerLevel.CRITICAL, "Windows 删除目录"),
    r"format\s+[a-z]:": (DangerLevel.CRITICAL, "格式化磁盘"),
    
    # System modification
    r"systeminfo": (DangerLevel.HIGH, "获取系统信息"),
    r"reg\s+(delete|add)": (DangerLevel.HIGH, "修改注册表"),
    r"netsh\s+firewall": (DangerLevel.HIGH, "修改防火墙"),
    r"shutdown": (DangerLevel.HIGH, "关闭系统"),
    
    # Network operations
    r"curl.*\|.*bash": (DangerLevel.MEDIUM, "远程脚本执行"),
    r"wget.*\|.*bash": (DangerLevel.MEDIUM, "远程脚本执行"),
    r"Invoke-WebRequest": (DangerLevel.MEDIUM, "下载并执行"),
    r"powershell.*-Command": (DangerLevel.MEDIUM, "执行命令"),
    
    # Environment
    r"export\s+PASSWORD": (DangerLevel.MEDIUM, "设置环境变量"),
    r"setx\s+": (DangerLevel.MEDIUM, "设置环境变量"),
    r"chmod\s+777": (DangerLevel.MEDIUM, "过度开放权限"),
    
    # Process
    r"kill\s+(-9|-SIGKILL)": (DangerLevel.HIGH, "强制终止进程"),
    r"taskkill": (DangerLevel.HIGH, "终止进程"),
    
    # Git (destructive)
    r"git\s+push\s+--force": (DangerLevel.MEDIUM, "强制推送"),
    r"git\s+push\s+--all": (DangerLevel.MEDIUM, "推送所有分支"),
    r"git\s+reset\s+--hard": (DangerLevel.MEDIUM, "硬重置"),
    r"git\s+clean\s+-fd": (DangerLevel.MEDIUM, "清理未跟踪文件"),
    
    # Package managers
    r"npm\s+install\s+-g": (DangerLevel.LOW, "全局安装"),
    r"pip\s+install\s+--user": (DangerLevel.LOW, "用户安装"),
    r"pip\s+uninstall": (DangerLevel.LOW, "卸载包"),
}

SAFE_COMMANDS = [
    r"^python\s",
    r"^python3\s",
    r"^node\s",
    r"^npm\s+(run|install|start|build|test|dev|lint|create|init)",
    r"^npx\s+(create|init)",
    r"^pip\s+install\s+\w+",
    r"^git\s+(status|log|diff|branch|checkout|pull|fetch|clone|init|add|commit)",
    r"^pytest\s",
    r"^uvicorn\s",
    r"^cargo\s+(build|run|test)",
    r"^vite\s",
    r"^eslint\s",
    r"^prettier\s",
]


@dataclass
class CommandWarning:
    """Command warning"""
    command: str
    danger_level: DangerLevel
    reason: str
    suggestion: Optional[str] = None


@dataclass
class PendingConfirmation:
    """Pending user confirmation"""
    id: str
    session_id: str
    command: str
    warning: CommandWarning
    created_at: float = field(default_factory=time.time)
    expires_at: float = None


class PermissionManager:
    """Permission manager with confirmation"""
    
    _pending: Dict[str, PendingConfirmation] = {}
    _lock = Lock()
    _confirm_callback: Optional[Callable] = None
    
    # User preferences (stored persistently)
    _saved_permissions: Dict[str, str] = {}  # pattern -> allow/deny
    
    @classmethod
    def check_command(cls, command: str) -> CommandWarning:
        """Check if command is dangerous"""
        # Check saved permissions first
        for pattern, perm in cls._saved_permissions.items():
            if re.search(pattern, command):
                return CommandWarning(
                    command=command,
                    danger_level=DangerLevel.SAFE if perm == "allow" else DangerLevel.HIGH,
                    reason=f"Saved permission: {perm}"
                )
        
        # Check against dangerous patterns
        for pattern, (level, reason) in DANGEROUS_PATTERNS.items():
            if re.search(pattern, command, re.IGNORECASE):
                return CommandWarning(
                    command=command,
                    danger_level=level,
                    reason=reason,
                    suggestion=cls._get_suggestion(pattern)
                )
        
        # Check if it's a safe command
        for safe_pattern in SAFE_COMMANDS:
            if re.match(safe_pattern, command, re.IGNORECASE):
                return CommandWarning(
                    command=command,
                    danger_level=DangerLevel.SAFE,
                    reason="Known safe command"
                )
        
        # Unknown command - medium risk
        return CommandWarning(
            command=command,
            danger_level=DangerLevel.MEDIUM,
            reason="Unknown command - proceed with caution"
        )
    
    @classmethod
    def _get_suggestion(cls, pattern: str) -> str:
        """Get suggestion for dangerous pattern"""
        suggestions = {
            r"rm\s+-rf": "Use 'rm -r' without -f for more safety, or specify exact path",
            r"del\s+/[s]": "Use recycle bin or specify explicit file",
            r"git\s+push\s+--force": "Use 'git push' without --force, or use --force-with-lease",
            r"git\s+reset\s+--hard": "Use 'git reset --soft' to keep changes staged",
        }
        return suggestions.get(pattern, "Review the command carefully before proceeding")
    
    @classmethod
    def needs_confirmation(cls, warning: CommandWarning) -> bool:
        """Check if command needs user confirmation"""
        return warning.danger_level in [
            DangerLevel.MEDIUM,
            DangerLevel.HIGH,
            DangerLevel.CRITICAL
        ]
    
    @classmethod
    def create_pending(cls, session_id: str, warning: CommandWarning) -> str:
        """Create pending confirmation"""
        import uuid
        pending_id = str(uuid.uuid4())[:8]
        
        pending = PendingConfirmation(
            id=pending_id,
            session_id=session_id,
            command=warning.command,
            warning=warning,
            expires_at=time.time() + 300  # 5 minutes
        )
        
        with cls._lock:
            cls._pending[pending_id] = pending
        
        return pending_id
    
    @classmethod
    def confirm(cls, pending_id: str, allow: bool) -> bool:
        """Confirm or deny pending command"""
        with cls._lock:
            pending = cls._pending.pop(pending_id, None)
        
        if not pending:
            return False
        
        if allow:
            # Save permission pattern
            cmd = pending.command
            # Extract simple pattern
            for safe in SAFE_COMMANDS:
                if re.match(safe, cmd, re.IGNORECASE):
                    cls._saved_permissions[safe] = "allow"
                    break
        
        return allow
    
    @classmethod
    def get_pending(cls, pending_id: str) -> Optional[PendingConfirmation]:
        """Get pending confirmation"""
        with cls._lock:
            return cls._pending.get(pending_id)
    
    @classmethod
    def cleanup_expired(cls):
        """Clean up expired confirmations"""
        now = time.time()
        with cls._lock:
            expired = [
                pid for pid, p in cls._pending.items()
                if p.expires_at and now > p.expires_at
            ]
            for pid in expired:
                cls._pending.pop(pid, None)
    
    @classmethod
    def set_confirm_callback(cls, callback: Callable):
        """Set callback for confirmations"""
        cls._confirm_callback = callback
    
    @classmethod
    def on_confirm(cls, pending_id: str, allow: bool):
        """Handle confirmation"""
        if cls._confirm_callback:
            cls._confirm_callback(pending_id, allow)


def format_warning_message(warning: CommandWarning) -> str:
    """Format warning message for user"""
    level_icons = {
        DangerLevel.SAFE: "✓",
        DangerLevel.LOW: "⚠",
        DangerLevel.MEDIUM: "⚠⚠",
        DangerLevel.HIGH: "⛔",
        DangerLevel.CRITICAL: "⛔⛔",
    }
    
    icon = level_icons.get(warning.danger_level, "?")
    level = warning.danger_level.value.upper()
    
    msg = f"\n{icon} **DANGER: {level}**\n"
    msg += f"Command: `{warning.command}`\n"
    msg += f"Reason: {warning.reason}\n"
    
    if warning.suggestion:
        msg += f"\nTip: {warning.suggestion}\n"
    
    return msg


__all__ = [
    "PermissionManager",
    "CommandWarning", 
    "PendingConfirmation",
    "DangerLevel",
    "DANGEROUS_PATTERNS",
    "SAFE_COMMANDS",
    "format_warning_message"
]