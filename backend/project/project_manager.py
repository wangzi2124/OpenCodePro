import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ProjectState:
    """Project state - tracks project context"""
    directory: str
    files: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    vcs: str = "git"
    ignore_patterns: List[str] = field(default_factory=list)


@dataclass  
class ProjectInstance:
    """Project instance - manages project state"""
    id: str
    state: ProjectState
    session_ids: List[str] = field(default_factory=list)


class ProjectManager:
    """Project manager - manages multiple projects"""
    
    _projects: Dict[str, ProjectInstance] = {}
    _current: Optional[str] = None
    
    DEFAULT_IGNORE = [
        "__pycache__",
        "*.pyc",
        ".git",
        "node_modules",
        ".venv",
        "venv",
        ".env",
        "dist",
        "build",
        "*.log",
    ]
    
    @classmethod
    def get_directory(cls, directory: str = None) -> str:
        """Get project directory"""
        directory = directory or os.getcwd()
        return os.path.abspath(directory)
    
    @classmethod
    def load(cls, directory: str = None) -> ProjectInstance:
        """Load project"""
        directory = cls.get_directory(directory)
        
        if directory in cls._projects:
            return cls._projects[directory]
        
        state = cls._load_state(directory)
        
        instance = ProjectInstance(
            id=directory,
            state=state
        )
        
        cls._projects[directory] = instance
        cls._current = directory
        
        return instance
    
    @classmethod
    def _load_state(cls, directory: str) -> ProjectState:
        """Load project state"""
        state = ProjectState(directory=directory)
        
        # Load .git
        git_dir = os.path.join(directory, ".git")
        if os.path.exists(git_dir):
            state.vcs = "git"
        
        # Load package.json
        package_json = os.path.join(directory, "package.json")
        if os.path.exists(package_json):
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    pkg = json.load(f)
                    state.dependencies = pkg.get("dependencies", {})
            except Exception:
                pass
        
        # Load pyproject.toml
        pyproject = os.path.join(directory, "pyproject.toml")
        if os.path.exists(pyproject):
            try:
                with open(pyproject, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "[project]" in content:
                        state.config["python"] = True
            except Exception:
                pass
        
        # Load .gitignore
        gitignore = os.path.join(directory, ".gitignore")
        if os.path.exists(gitignore):
            try:
                with open(gitignore, 'r', encoding='utf-8') as f:
                    state.ignore_patterns = [
                        line.strip() 
                        for line in f 
                        if line.strip() and not line.startswith("#")
                    ]
            except Exception:
                pass
        
        if not state.ignore_patterns:
            state.ignore_patterns = cls.DEFAULT_IGNORE
        
        # List files
        state.files = cls._list_files(directory, state.ignore_patterns)
        
        return state
    
    @classmethod
    def _list_files(cls, directory: str, ignore_patterns: List[str]) -> List[str]:
        """List project files"""
        files = []
        
        try:
            for root, dirs, filenames in os.walk(directory):
                # Filter directories
                dirs[:] = [d for d in dirs if d not in ignore_patterns and not d.startswith(".")]
                
                for filename in filenames:
                    if any(p in filename for p in ignore_patterns):
                        continue
                    if filename.startswith("."):
                        continue
                    
                    rel_path = os.path.relpath(os.path.join(root, filename), directory)
                    files.append(rel_path)
        except Exception:
            pass
        
        return files[:100]  # Limit
    
    @classmethod
    def get(cls, directory: str = None) -> Optional[ProjectInstance]:
        """Get project"""
        directory = cls.get_directory(directory)
        return cls._projects.get(directory)
    
    @classmethod
    def get_current(cls) -> Optional[ProjectInstance]:
        """Get current project"""
        if cls._current:
            return cls._projects.get(cls._current)
        return cls.load()
    
    @classmethod
    def get_context(cls, directory: str = None, max_files: int = 20) -> str:
        """Get project context as string"""
        project = cls.load(directory)
        state = project.state
        
        lines = [f"Project Directory: {state.directory}"]
        lines.append(f"VCS: {state.vcs}")
        
        if state.dependencies:
            deps = ", ".join(list(state.dependencies.keys())[:5])
            lines.append(f"Dependencies: {deps}")
        
        lines.append(f"\nFiles ({len(state.files)}):")
        for f in state.files[:max_files]:
            lines.append(f"  - {f}")
        
        if len(state.files) > max_files:
            lines.append(f"  ... and {len(state.files) - max_files} more")
        
        return "\n".join(lines)
    
    @classmethod
    def get_info(cls, directory: str = None) -> Dict[str, Any]:
        """Get project info"""
        instance = cls.load(directory)
        state = instance.state

        return {
            "id": instance.id,
            "directory": state.directory,
            "files": state.files[:50],
            "dependencies": state.dependencies,
            "vcs": state.vcs,
            "config": state.config
        }

    @classmethod
    def dispose(cls, directory: str = None):
        """Dispose project"""
        directory = cls.get_directory(directory)
        cls._projects.pop(directory, None)
        if cls._current == directory:
            cls._current = None


__all__ = ["ProjectState", "ProjectInstance", "ProjectManager"]