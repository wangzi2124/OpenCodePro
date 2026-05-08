import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class PatchType(str, Enum):
    ADD = "add"
    DELETE = "delete"
    UPDATE = "update"
    MOVE = "move"


@dataclass
class FileChange:
    """Single file change"""
    path: str
    type: PatchType
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class Patch:
    """Patch - tracks file changes"""
    id: str
    description: str
    changes: List[FileChange] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    parent_id: Optional[str] = None


class PatchManager:
    """Patch manager - tracks and reverts file changes"""
    
    _patches: Dict[str, Patch] = {}
    _current_id: Optional[str] = None
    _file_hashes: Dict[str, str] = {}
    
    @classmethod
    def _hash_content(cls, content: str) -> str:
        """Hash file content"""
        return hashlib.md5(content.encode()).hexdigest()
    
    @classmethod
    def create_patch(cls, description: str) -> str:
        """Create new patch"""
        patch_id = str(time.time())
        
        patch = Patch(
            id=patch_id,
            description=description,
            parent_id=cls._current_id,
            changes=[]
        )
        
        cls._patches[patch_id] = patch
        cls._current_id = patch_id
        
        return patch_id
    
    @classmethod
    def add_change(cls, patch_id: str, path: str, change_type: PatchType, 
                 old_content: str = None, new_content: str = None):
        """Add change to patch"""
        patch = cls._patches.get(patch_id)
        if not patch:
            return
        
        change = FileChange(
            path=path,
            type=change_type,
            old_content=old_content,
            new_content=new_content
        )
        
        patch.changes.append(change)
        
        # Track file hash
        if new_content:
            cls._file_hashes[path] = cls._hash_content(new_content)
    
    @classmethod
    def record_change(cls, path: str, new_content: str):
        """Record a file change"""
        if not cls._current_id:
            cls.create_patch("Auto-saved changes")
        
        old_content = None
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
            except Exception:
                pass
        
        change_type = PatchType.UPDATE
        if not old_content and new_content:
            change_type = PatchType.ADD
        elif old_content and not new_content:
            change_type = PatchType.DELETE
        
        cls.add_change(cls._current_id, path, change_type, old_content, new_content)
    
    @classmethod
    def get_patch(cls, patch_id: str) -> Optional[Patch]:
        """Get patch by ID"""
        return cls._patches.get(patch_id)
    
    @classmethod
    def get_current(cls) -> Optional[Patch]:
        """Get current patch"""
        if cls._current_id:
            return cls._patches.get(cls._current_id)
        return None
    
    @classmethod
    def revert(cls, patch_id: str = None, dry_run: bool = False) -> Dict[str, Any]:
        """Revert patch"""
        patch_id = patch_id or cls._current_id
        patch = cls._patches.get(patch_id)
        
        if not patch:
            return {"success": False, "error": "Patch not found"}
        
        results = {"reverted": [], "errors": []}
        
        for change in patch.changes:
            if change.type == PatchType.DELETE:
                if dry_run:
                    results["reverted"].append(f"Would delete {change.path}")
                else:
                    try:
                        if os.path.exists(change.path):
                            os.remove(change.path)
                            results["reverted"].append(f"Deleted {change.path}")
                    except Exception as e:
                        results["errors"].append(f"Error deleting {change.path}: {e}")
            
            elif change.type == PatchType.UPDATE:
                if dry_run:
                    results["reverted"].append(f"Would restore {change.path}")
                else:
                    try:
                        with open(change.path, 'w', encoding='utf-8') as f:
                            f.write(change.old_content or "")
                        results["reverted"].append(f"Restored {change.path}")
                    except Exception as e:
                        results["errors"].append(f"Error restoring {change.path}: {e}")
            
            elif change.type == PatchType.ADD:
                if dry_run:
                    results["reverted"].append(f"Would remove {change.path}")
                else:
                    try:
                        if os.path.exists(change.path):
                            os.remove(change.path)
                            results["reverted"].append(f"Removed {change.path}")
                    except Exception as e:
                        results["errors"].append(f"Error removing {change.path}: {e}")
        
        if not dry_run:
            cls._current_id = patch.parent_id
        
        return results
    
    @classmethod
    def compact(cls, max_patches: int = 10) -> int:
        """Compact patches - remove old patches"""
        # Keep only recent patches
        patch_ids = sorted(cls._patches.keys(), reverse=True)
        
        removed = 0
        for patch_id in patch_ids[max_patches:]:
            cls._patches.pop(patch_id, None)
            removed += 1
        
        return removed
    
    @classmethod
    def list(cls) -> List[Dict]:
        """List all patches"""
        return [
            {
                "id": p.id,
                "description": p.description,
                "changes": len(p.changes),
                "timestamp": p.timestamp
            }
            for p in cls._patches.values()
        ]


__all__ = ["Patch", "FileChange", "PatchManager", "PatchType"]