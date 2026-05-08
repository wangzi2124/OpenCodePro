import os
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class GitError(Exception):
    pass


class GitStatus(str, Enum):
    CLEAN = "clean"
    DIRTY = "dirty"
    UNTRACKED = "untracked"


@dataclass
class GitCommit:
    """Git commit"""
    hash: str
    message: str
    author: str
    timestamp: str


@dataclass
class GitDiff:
    """Git diff"""
    file: str
    status: str
    changes: str


class GitClient:
    """Git client"""
    
    @staticmethod
    def _run_command(directory: str, args: List[str]) -> Tuple[str, str]:
        """Run git command"""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=directory,
                capture_output=True,
                text=True
            )
            return result.stdout, result.stderr
        except FileNotFoundError:
            raise GitError("Git not found")
    
    @staticmethod
    def status(directory: str) -> str:
        """Get git status"""
        stdout, stderr = GitClient._run_command(directory, ["status", "--porcelain"])
        
        if not stdout.strip():
            return "clean"
        
        lines = stdout.strip().split('\n')
        status = []
        
        for line in lines:
            if len(line) >= 3:
                status.append(line[:3])
        
        return '\n'.join(status) if status else "clean"
    
    @staticmethod
    def diff(directory: str, file: str = None) -> str:
        """Get git diff"""
        args = ["diff"]
        
        if file:
            args.append("--")
            args.append(file)
        
        stdout, stderr = GitClient._run_command(directory, args)
        return stdout or stderr
    
    @staticmethod
    def log(directory: str, limit: int = 10) -> List[GitCommit]:
        """Get git log"""
        stdout, stderr = GitClient._run_command(
            directory,
            [
                "log",
                f"-{limit}",
                "--format=%H|%s|%an",
                "--date=iso"
            ]
        )

        commits = []

        for line in stdout.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    commits.append(GitCommit(
                        hash=parts[0],
                        message=parts[1],
                        author=parts[2],
                        timestamp=""
                    ))

        return commits
    
    @staticmethod
    def branch(directory: str) -> str:
        """Get current branch"""
        stdout, _ = GitClient._run_command(directory, ["branch", "--show-current"])
        return stdout.strip()
    
    @staticmethod
    def add(directory: str, files: List[str] = None) -> str:
        """Stage files"""
        args = ["add"]
        
        if files:
            args.extend(files)
        else:
            args.append(".")
        
        stdout, stderr = GitClient._run_command(directory, args)
        return stdout or stderr
    
    @staticmethod
    def commit(directory: str, message: str) -> str:
        """Create commit"""
        # Stage all
        GitClient._run_command(directory, ["add", "."])
        
        # Commit
        stdout, stderr = GitClient._run_command(directory, ["commit", "-m", message])
        return stdout or stderr
    
    @staticmethod
    def checkout(directory: str, branch: str, create: bool = False) -> str:
        """Checkout branch"""
        args = ["checkout"]
        
        if create:
            args.append("-b")
        
        args.append(branch)
        
        stdout, stderr = GitClient._run_command(directory, args)
        return stdout or stderr
    
    @staticmethod
    def revert(directory: str, file: str) -> str:
        """Revert file to HEAD"""
        stdout, stderr = GitClient._run_command(directory, ["checkout", "--", file])
        return stdout or stderr
    
    @staticmethod
    def is_repo(directory: str) -> bool:
        """Check if directory is a git repo"""
        git_dir = os.path.join(directory, ".git")
        return os.path.exists(git_dir)


__all__ = ["GitClient", "GitCommit", "GitDiff", "GitStatus", "GitError"]