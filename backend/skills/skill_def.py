import os
import json
import glob as glob_module
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel


@dataclass
class Skill:
    """Skill definition - custom AI prompt templates"""
    name: str
    description: str
    prompt: str
    tools: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


class SkillRegistry:
    """Skill registry - manages available skills"""
    
    _skills: Dict[str, Skill] = {}
    _initialized: bool = False
    
    @classmethod
    def initialize(cls, project_dir: str = None):
        if cls._initialized:
            return
        
        project_dir = project_dir or os.getcwd()
        
        # Built-in skills
        cls._skills = {
            "read": Skill(
                name="read",
                description="Reading and understanding code",
                prompt="""You are a code reading expert. Analyze the provided code and explain:
1. What the code does
2. Key functions and their purpose
3. Any important patterns or conventions used

Provide a clear, concise explanation.""",
                tools=["read_file", "glob_search", "grep_search"],
            ),
            "write": Skill(
                name="write",
                description="Writing code based on requirements",
                prompt="""You are a code writing expert. Write clean, working code that:
1. Follows best practices for the language
2. Is well-documented with comments
3. Handles edge cases appropriately

Write complete, production-ready code.""",
                tools=["write_file", "read_file", "edit_file"],
            ),
            "refactor": Skill(
                name="refactor",
                description="Refactoring existing code",
                prompt="""You are a refactoring expert. Improve code quality while preserving functionality:
1. Remove code duplication
2. Improve naming and organization
3. Add appropriate abstractions
4. Maintain backward compatibility

Explain each change you make.""",
                tools=["read_file", "edit_file", "glob_search"],
            ),
            "debug": Skill(
                name="debug",
                description="Debugging and fixing issues",
                prompt="""You are a debugging expert. Find and fix issues in code:
1. Analyze error messages and stack traces
2. Identify root causes
3. Propose and implement fixes
4. Verify the fix works

Be methodical and explain your reasoning.""",
                tools=["read_file", "grep_search", "run_bash"],
            ),
            "test": Skill(
                name="test",
                description="Writing and running tests",
                prompt="""You are a testing expert. Write comprehensive tests:
1. Cover normal cases and edge cases
2. Use appropriate test frameworks
3. Mock external dependencies
4. Verify tests pass

Focus on testing behavior, not implementation.""",
                tools=["write_file", "read_file", "run_bash"],
            ),
            "explain": Skill(
                name="explain",
                description="Explaining code to users",
                prompt="""You are a code explanation expert. Explain code clearly:
1. Start with high-level overview
2. Explain key concepts simply
3. Give concrete examples
4. Answer follow-up questions

Use layman terms when possible.""",
                tools=["read_file", "glob_search", "grep_search"],
            ),
            "review": Skill(
                name="review",
                description="Code review and suggestions",
                prompt="""You are a code review expert. Review code for:
1. Bugs and potential issues
2. Security vulnerabilities
3. Performance problems
4. Code quality and style

Provide specific, actionable feedback.""",
                tools=["read_file", "grep_search"],
            ),
        }
        
        # Load custom skills from project directory
        cls._load_custom_skills(project_dir)
        
        cls._initialized = True
    
    @classmethod
    def _load_custom_skills(cls, project_dir: str):
        """Load custom skills from .opencode/skills directory"""
        skills_dir = os.path.join(project_dir, ".opencode", "skills")
        
        if not os.path.exists(skills_dir):
            return
        
        for skill_file in glob_module.glob(os.path.join(skills_dir, "*.json")):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    skill_data = json.load(f)
                
                skill = Skill(
                    name=skill_data.get("name", os.path.basename(skill_file, ".json")),
                    description=skill_data.get("description", ""),
                    prompt=skill_data.get("prompt", ""),
                    tools=skill_data.get("tools", []),
                    options=skill_data.get("options", {}),
                )
                cls._skills[skill.name] = skill
            except Exception:
                pass
    
    @classmethod
    def get(cls, name: str) -> Optional[Skill]:
        cls.initialize()
        return cls._skills.get(name)
    
    @classmethod
    def list(cls) -> List[Skill]:
        cls.initialize()
        return list(cls._skills.values())
    
    @classmethod
    def register(cls, skill: Skill):
        cls._skills[skill.name] = skill
    
    @classmethod
    def invoke(cls, name: str, context: Dict) -> str:
        """Invoke a skill with context"""
        skill = cls.get(name)
        if not skill:
            return f"Skill '{name}' not found"
        
        # Skills return their prompt for use by the agent
        return skill.prompt


__all__ = ["Skill", "SkillRegistry"]