import os

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_SESSION_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "session", "prompts")
_TOOL_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "prompts")
_COMMAND_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "command", "templates")


def _load_prompt(filepath: str, fallback: str = "") -> str:
    """Load a prompt from a .txt file, returning fallback if not found."""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return fallback


def load_session_prompt(model_name: str) -> str:
    """Load model-specific system prompt, falling back by model family then generic."""
    model_lower = model_name.lower()
    
    family_map = {
        "claude": "anthropic",
        "anthropic": "anthropic",
        "gpt": "beast",
        "o1": "beast",
        "o3": "beast",
        "gemini": "gemini",
        "qwen": "qwen",
        "codestral": "beast",
        "mixtral": "qwen",
        "llama": "qwen",
        "deepseek": "qwen",
        "codex": "codex",
        "copilot": "copilot-gpt-5",
    }
    
    candidates = []
    for key, filename in family_map.items():
        if key in model_lower:
            candidates.append(filename)
    
    # Try exact match, then family matches, then default to anthropic
    for name in [model_lower] + candidates + ["anthropic"]:
        filepath = os.path.join(_SESSION_PROMPTS_DIR, f"{name}.txt")
        content = _load_prompt(filepath)
        if content:
            return content
    
    return _load_prompt(os.path.join(_SESSION_PROMPTS_DIR, "anthropic.txt"),
                        fallback="You are OpenCode Pro, an AI coding assistant.")


def load_tool_prompt(tool_name: str) -> str:
    """Load a tool description prompt from .txt file."""
    filepath = os.path.join(_TOOL_PROMPTS_DIR, f"{tool_name}.txt")
    return _load_prompt(filepath)


def load_command_template(name: str) -> str:
    """Load a command template from .txt file."""
    filepath = os.path.join(_COMMAND_TEMPLATES_DIR, f"{name}.txt")
    return _load_prompt(filepath)


# Agent prompts - loaded from .txt files with hardcoded fallbacks
COMPACTION_PROMPT = _load_prompt(
    os.path.join(_PROMPTS_DIR, "compaction.txt"),
    fallback="""You are a conversation compaction agent. Create a compressed version that preserves key information.

Preserve:
- Original user intent
- Key code changes
- Important decisions
- Error resolutions

Remove:
- Redundant explanations
- Failed attempts
- Verbose debugging steps"""
)

TITLE_PROMPT = _load_prompt(
    os.path.join(_PROMPTS_DIR, "title.txt"),
    fallback="""You are a title generator. Output ONLY a thread title. Nothing else.

Rules:
- Use -ing verbs for actions
- Keep technical terms exact
- Output must be ≤50 characters
- Never use tools"""
)

SUMMARY_PROMPT = _load_prompt(
    os.path.join(_PROMPTS_DIR, "summary.txt"),
    fallback="""Provide a comprehensive yet concise summary of the conversation.

Include: main goal, key actions, important outcomes, open items.
Keep it brief (2-4 sentences)."""
)

EXPLORE_PROMPT = _load_prompt(
    os.path.join(_PROMPTS_DIR, "explore.txt"),
    fallback="""You are a code exploration expert. Explore codebases quickly and accurately.

1. Start broad, then narrow down
2. Use glob patterns to find files
3. Use grep to search patterns
4. Provide file locations with line numbers"""
)

GENERATE_PROMPT = _load_prompt(
    os.path.join(_PROMPTS_DIR, "generate.txt"),
    fallback="""You are an AI coding assistant. Write complete, working code.

Follow best practices, handle edge cases, include imports.
Plan first, implement, then verify."""
)

# Session model prompts cache
_MODEL_PROMPT_CACHE: dict = {}

def get_model_prompt(model: str) -> str:
    """Get cached model-specific system prompt."""
    if model not in _MODEL_PROMPT_CACHE:
        _MODEL_PROMPT_CACHE[model] = load_session_prompt(model)
    return _MODEL_PROMPT_CACHE[model]

# Mode/management prompts
PLAN_PROMPT = _load_prompt(os.path.join(_SESSION_PROMPTS_DIR, "plan.txt"), "")
BUILD_SWITCH_PROMPT = _load_prompt(os.path.join(_SESSION_PROMPTS_DIR, "build-switch.txt"), "")
MAX_STEPS_PROMPT = _load_prompt(os.path.join(_SESSION_PROMPTS_DIR, "max-steps.txt"), "")

__all__ = [
    "COMPACTION_PROMPT",
    "TITLE_PROMPT",
    "SUMMARY_PROMPT",
    "EXPLORE_PROMPT",
    "GENERATE_PROMPT",
    "PLAN_PROMPT",
    "BUILD_SWITCH_PROMPT",
    "MAX_STEPS_PROMPT",
    "load_session_prompt",
    "load_tool_prompt",
    "load_command_template",
    "get_model_prompt",
]