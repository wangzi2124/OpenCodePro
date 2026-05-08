import os
import re
import json
import fnmatch
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel


class AgentMode(str, Enum):
    SUBAGENT = "subagent"
    PRIMARY = "primary"
    ALL = "all"


class Permission(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionChecker:
    """Permission checker - implements allow/ask/deny for tool calls"""
    
    @staticmethod
    def check(tool_name: str, args: Dict, permission: Dict[str, Any]) -> tuple[bool, str]:
        """Check if a tool call is allowed
        
        Returns: (is_allowed, status)
          - (True, "allow") - allowed
          - (False, "deny") - denied  
          - (None, "ask") - needs user confirmation
        """
        if not permission:
            return True, "allow"
        
        # Check edit permission (for write/edit tools)
        if tool_name in ["write_file", "edit_file", "batch_edit", "multi_edit"]:
            edit_perm = permission.get("edit", Permission.ALLOW)
            if edit_perm == Permission.DENY:
                return False, "deny"
            elif edit_perm == Permission.ASK:
                return None, "ask"
            return True, "allow"
        
        # Check bash permission
        if tool_name == "run_bash":
            bash_perms = permission.get("bash", {"*": Permission.ALLOW})
            command = args.get("command", "")
            
            for pattern, perm in bash_perms.items():
                if fnmatch.fnmatch(command, pattern):
                    if perm == Permission.DENY:
                        return False, "deny"
                    elif perm == Permission.ASK:
                        return None, "ask"
                    return True, "allow"
            
            default_perm = bash_perms.get("*", Permission.ALLOW)
            if default_perm == Permission.DENY:
                return False, "deny"
            elif default_perm == Permission.ASK:
                return None, "ask"
            return True, "allow"
        
        # Check skill permission
        if tool_name in ["skill_invoke", "skill_list"]:
            skill_perms = permission.get("skill", {"*": Permission.ALLOW})
            skill_name = args.get("name", "")
            
            for pattern, perm in skill_perms.items():
                if fnmatch.fnmatch(skill_name, pattern):
                    if perm == Permission.DENY:
                        return False, "deny"
                    elif perm == Permission.ASK:
                        return None, "ask"
                    return True, "allow"
            
            default_perm = skill_perms.get("*", Permission.ALLOW)
            if default_perm == Permission.DENY:
                return False, "deny"
            elif default_perm == Permission.ASK:
                return None, "ask"
            return True, "allow"
        
        # Check webfetch permission
        if tool_name in ["fetch_url", "web_search"]:
            web_perm = permission.get("webfetch", Permission.ALLOW)
            if web_perm == Permission.DENY:
                return False, "deny"
            elif web_perm == Permission.ASK:
                return None, "ask"
            return True, "allow"
        
        # Default allow
        return True, "allow"


@dataclass
class AgentInfo:
    name: str
    description: Optional[str] = None
    mode: AgentMode = AgentMode.PRIMARY
    native: bool = False
    hidden: bool = False
    default: bool = False
    top_p: Optional[float] = None
    temperature: Optional[float] = None
    color: Optional[str] = None
    model: Optional[Dict[str, str]] = None
    prompt: Optional[str] = None
    tools: Dict[str, bool] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    permission: Optional[Dict[str, Any]] = None
    max_steps: Optional[int] = None


class AgentRegistry:
    _agents: Dict[str, AgentInfo] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return
        
        cls._agents = {
            "build": AgentInfo(
                name="build",
                mode=AgentMode.PRIMARY,
                native=True,
                permission={
                    "edit": Permission.ALLOW,
                    "bash": {"*": Permission.ALLOW},
                    "skill": {"*": Permission.ALLOW},
                    "webfetch": Permission.ALLOW,
                },
                tools={},
                options={},
            ),
            "plan": AgentInfo(
                name="plan",
                mode=AgentMode.PRIMARY,
                native=True,
                permission={
                    "edit": Permission.DENY,
                    "bash": {
                        "cut*": Permission.ALLOW,
                        "diff*": Permission.ALLOW,
                        "du*": Permission.ALLOW,
                        "git diff*": Permission.ALLOW,
                        "git log*": Permission.ALLOW,
                        "git status*": Permission.ALLOW,
                        "grep*": Permission.ALLOW,
                        "head*": Permission.ALLOW,
                        "ls*": Permission.ALLOW,
                        "pwd*": Permission.ALLOW,
                        "rg*": Permission.ALLOW,
                        "sort*": Permission.ALLOW,
                        "tail*": Permission.ALLOW,
                        "tree*": Permission.ALLOW,
                        "wc*": Permission.ALLOW,
                        "*": Permission.ASK,
                    },
                    "webfetch": Permission.ALLOW,
                },
                tools={},
                options={},
            ),
            "explore": AgentInfo(
                name="explore",
                description="Fast agent specialized for exploring codebases. Use this when you need to quickly find files by patterns, search code for keywords, or answer questions about the codebase.",
                mode=AgentMode.SUBAGENT,
                native=True,
                permission={
                    "edit": Permission.DENY,
                    "bash": {"*": Permission.DENY},
                    "webfetch": Permission.ALLOW,
                },
                tools={
                    "todoread": False,
                    "todowrite": False,
                    "edit": False,
                    "write": False,
                },
                options={},
            ),
            "general": AgentInfo(
                name="general",
                description="General-purpose agent for researching complex questions and executing multi-step tasks.",
                mode=AgentMode.SUBAGENT,
                native=True,
                hidden=True,
                permission={
                    "edit": Permission.ALLOW,
                    "bash": {"*": Permission.ALLOW},
                    "webfetch": Permission.ALLOW,
                },
                tools={
                    "todoread": False,
                    "todowrite": False,
                },
                options={},
            ),
            "compaction": AgentInfo(
                name="compaction",
                mode=AgentMode.PRIMARY,
                native=True,
                hidden=True,
                tools={"*": False},
                options={},
            ),
            "title": AgentInfo(
                name="title",
                mode=AgentMode.PRIMARY,
                native=True,
                hidden=True,
                tools={},
                options={},
            ),
            "summary": AgentInfo(
                name="summary",
                mode=AgentMode.PRIMARY,
                native=True,
                hidden=True,
                tools={},
                options={},
            ),
        }
        cls._initialized = True

    @classmethod
    def get(cls, name: str) -> Optional[AgentInfo]:
        cls.initialize()
        return cls._agents.get(name)

    @classmethod
    def list(cls) -> List[AgentInfo]:
        cls.initialize()
        return [a for a in cls._agents.values() if not a.hidden]

    @classmethod
    def check_permission(cls, agent_name: str, tool_name: str, args: Dict) -> tuple[bool, str]:
        """Check if a tool call is allowed for the given agent"""
        agent = cls.get(agent_name)
        if not agent or not agent.permission:
            return True, "allow"
        
        return PermissionChecker.check(tool_name, args, agent.permission)


__all__ = ["AgentInfo", "AgentRegistry", "AgentMode", "Permission", "PermissionChecker"]