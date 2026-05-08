import os
import re
import asyncio
import logging
import uuid
import time
import json
from typing import List, Optional, Dict, Any, AsyncGenerator
from pydantic import BaseModel
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool, BaseTool

from backend.agent.agent_def import AgentRegistry, AgentInfo, AgentMode, PermissionChecker
from backend.agent.prompts import COMPACTION_PROMPT, TITLE_PROMPT, SUMMARY_PROMPT, EXPLORE_PROMPT, GENERATE_PROMPT
from backend.session.session_manager import SessionManager
from backend.project.project_manager import ProjectManager
from backend.vcs.git_client import GitClient, GitError
from backend.mcp.mcp_client import MCPClient, MCPStatus
from backend.skills.skill_def import SkillRegistry
from backend.patch.patch_manager import PatchManager, PatchType
from backend.storage.storage_manager import StorageManager
from backend.provider.provider_manager import (
    ProviderManager, RetryHandler, init_providers,
    OpenAIProvider, AnthropicProvider, OllamaProvider
)

router = APIRouter()

MAX_TOKENS = 32000
MAX_MESSAGES = 20

init_providers()


def get_tools() -> List[BaseTool]:
    from backend.tools.chain_tools import TOOL_REGISTRY
    return TOOL_REGISTRY


class AgentRequest(BaseModel):
    query: str
    model: str = "qwen2.5:latest"
    endpoint: str = "http://localhost:11434"
    is_local: bool = True
    agent: str = "build"
    project_directory: Optional[str] = None
    history: Optional[List[Dict]] = None
    user_info: Optional[Dict] = None
    session_id: Optional[str] = None
    api_key: Optional[str] = None


def sse_event(event_type: str, data: Any = None, extra: Dict = None) -> str:
    payload = {"type": event_type}
    if data is not None:
        payload["data"] = data
    if extra:
        payload.update(extra)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def sse_heartbeat() -> str:
    return f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"


class TaskStep:
    def __init__(self, id: int, description: str, status: str = "pending"):
        self.id = id
        self.description = description
        self.status = status
        self.result = None
        self.tool_calls = []
        self.tool_name = None
        self.tool_args = {}
    
    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status,
            "result": self.result,
            "tool_calls": self.tool_calls
        }


class ContextEngine:
    def __init__(self, req: AgentRequest):
        self.req = req
        self.project_dir = req.project_directory or os.getcwd()
        
    def get_project_context(self) -> str:
        try:
            project_info = ProjectManager.get_info(self.project_dir)
            files = project_info.get("files", [])[:20]
            file_list = "\n".join(f"  - {f}" for f in files)
            dependencies = project_info.get("dependencies", {})
            deps_str = ""
            if dependencies:
                deps_str = "\nDependencies:"
                for name, version in list(dependencies.items())[:5]:
                    deps_str += f"\n  - {name}: {version}"

            return f"""Current Project: {self.project_dir}
Files:
{file_list}{deps_str}

VCS: {project_info.get('vcs', 'unknown')}"""
        except Exception as e:
            return f"Project: {self.project_dir}\n(Error: {e})"
    
    def get_user_context(self) -> str:
        if not self.req.user_info:
            return ""
        info = self.req.user_info
        return f"User: {info.get('name', 'Unknown')}\nLevel: {info.get('level', 'intermediate')}"
    
    def build_system_prompt(self, agent_info: AgentInfo) -> str:
        project_ctx = self.get_project_context()
        user_ctx = self.get_user_context()

        agent_prompts = {
            "build": GENERATE_PROMPT,
            "plan": "You are a technical planner. Analyze requirements and create plans.\n\nIMPORTANT: You are in READ-ONLY mode. Do NOT make any edits or run write operations. You may only read, search, and analyze.",
            "explore": EXPLORE_PROMPT,
            "general": "You are a research assistant. Use tools to find information and answer questions.",
            "compaction": COMPACTION_PROMPT,
            "title": TITLE_PROMPT,
            "summary": SUMMARY_PROMPT,
        }
        agent_prompt = agent_prompts.get(agent_info.name, "You are an AI programming assistant.")

        tools_descs = [f"- {t.name}: {t.description or ''}" for t in get_tools()]

        return f"""{agent_prompt}

Available tools:
{chr(10).join(tools_descs)}

{project_ctx}

{user_ctx}

Use tools when needed. Provide complete solutions."""
    
    def format_history_from_list(self, history: List[Dict]) -> List:
        if not history:
            return []

        messages = []
        for msg in history[-MAX_MESSAGES:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "tool":
                messages.append(ToolMessage(
                    content=content,
                    tool_call_id=msg.get("tool_call_id", "")
                ))

        return messages
    
    def truncate_if_needed(self, messages: List, max_tokens: int = MAX_TOKENS) -> List:
        if len(messages) <= MAX_MESSAGES:
            return messages
        
        system_msg = messages[0] if hasattr(messages[0], 'content') and messages[0].type == "system" else None
        
        if system_msg:
            return [system_msg] + messages[-(MAX_MESSAGES-1):]
        return messages[-MAX_MESSAGES:]


async def stream_llm_response(
    llm, tools: List[BaseTool], messages: List, 
    abort_event: asyncio.Event = None,
    max_iterations: int = 30
):
    accumulated_text = ""
    iteration = 0
    
    while iteration < max_iterations:
        if abort_event and abort_event.is_set():
            yield sse_event("abort", "Request cancelled")
            break
        
        iteration += 1
        logger.info(f"[ITERATION] {iteration}/{max_iterations}")
        
        try:
            llm_with_tools = llm.bind_tools(tools)
            
            response = await asyncio.to_thread(llm_with_tools.invoke, messages)
            
            tool_calls = getattr(response, 'tool_calls', None) or []
            
            if tool_calls:
                for tc in tool_calls:
                    tool_name = tc.get('name', '')
                    tool_args = tc.get('args', {})
                    tool_call_id = tc.get('id', '')
                    
                    yield sse_event("tool-start", {
                        "tool": tool_name,
                        "args": tool_args,
                        "call_id": tool_call_id
                    })
                    
                    is_allowed, status = PermissionChecker.check(tool_name, tool_args, {})
                    if not is_allowed:
                        result = f"Permission denied: {tool_name}"
                        yield sse_event("tool-end", {
                            "tool": tool_name,
                            "call_id": tool_call_id,
                            "result": result,
                            "error": "permission_denied"
                        })
                        messages.append(response)
                        messages.append(ToolMessage(content=result, tool_call_id=tool_call_id))
                        continue
                    
                    if status == "ask":
                        result = f"Permission needed: {tool_name} requires confirmation"
                        yield sse_event("tool-end", {
                            "tool": tool_name,
                            "call_id": tool_call_id,
                            "result": result,
                            "status": "pending_confirmation"
                        })
                        messages.append(response)
                        messages.append(ToolMessage(content=result, tool_call_id=tool_call_id))
                        continue
                    
                    tool_obj = next((t for t in tools if t.name == tool_name), None)
                    if tool_obj:
                        try:
                            result = tool_obj.invoke(tool_args)
                            logger.info(f"[TOOL_RESULT] {tool_name}: {str(result)[:200]}...")
                            yield sse_event("tool-end", {
                                "tool": tool_name,
                                "call_id": tool_call_id,
                                "result": str(result)[:500],
                                "status": "completed"
                            })
                            messages.append(response)
                            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))
                        except Exception as e:
                            error_msg = f"Error: {e}"
                            logger.error(f"[TOOL_ERROR] {tool_name}: {e}")
                            yield sse_event("tool-end", {
                                "tool": tool_name,
                                "call_id": tool_call_id,
                                "result": error_msg,
                                "error": str(e)
                            })
                            messages.append(response)
                            messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id))
                    else:
                        error_msg = f"Tool not found: {tool_name}"
                        yield sse_event("tool-end", {
                            "tool": tool_name,
                            "call_id": tool_call_id,
                            "result": error_msg,
                            "error": "tool_not_found"
                        })
                        messages.append(response)
                        messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id))
                
                yield sse_event("tool-loop-complete", {"iteration": iteration})
                continue
            
            output = getattr(response, 'content', '') or ""
            if output:
                yield sse_event("text-delta", {"text": output})
                accumulated_text += output
            
            yield sse_event("final-answer", {
                "content": output,
                "iteration": iteration
            })
            yield sse_event("complete", {"accumulated_text": accumulated_text})
            return
            
        except Exception as e:
            error_msg = str(e)
            retry_reason = RetryHandler.is_retryable(e)
            
            if retry_reason:
                delay = RetryHandler.calculate_delay(iteration, e)
                logger.warning(f"[RETRY] {retry_reason}, waiting {delay:.1f}s...")
                yield sse_event("retry", {
                    "reason": retry_reason,
                    "delay": delay,
                    "attempt": iteration
                })
                
                if abort_event:
                    try:
                        await asyncio.wait_for(asyncio.sleep(delay), timeout=delay)
                    except asyncio.TimeoutError:
                        yield sse_event("abort", "Retry cancelled")
                        break
                else:
                    time.sleep(min(delay, 10))
                continue
            
            logger.error(f"[ERROR] {error_msg}")
            yield sse_event("error", {"message": error_msg, "type": type(e).__name__})
            break
    
    if iteration >= max_iterations:
        yield sse_event("max-iterations", {"iterations": max_iterations, "accumulated": accumulated_text})


def create_llm(model: str, endpoint: str, is_local: bool, api_key: str = None):
    if is_local or "localhost" in endpoint or "ollama" in endpoint:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            base_url=endpoint,
            timeout=httpx.Timeout(300.0, connect=5.0),
        )
    
    if model.startswith("claude"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""),
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
    
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model,
        base_url=endpoint,
        api_key=api_key or "not-needed",
        timeout=httpx.Timeout(120.0, connect=10.0),
        streaming=True,
    )


@router.post("/agent/run")
async def run_agent(req: AgentRequest):
    session_id = req.session_id or str(uuid.uuid4())
    logger.info(f"[AGENT] Model: {req.model}, Agent: {req.agent}, Session: {session_id}")
    
    stored_session = StorageManager.get(f"session:{session_id}")
    stored_messages = stored_session.get("messages", []) if stored_session else []

    if req.history and len(req.history) > 0:
        history = req.history
        logger.info(f"[HISTORY] Using client history: {len(history)} messages")
    else:
        history = stored_messages
        logger.info(f"[HISTORY] Using stored history: {len(history)} messages")

    ctx_engine = ContextEngine(req)
    agent_info = AgentRegistry.get(req.agent) or AgentRegistry.get("build")

    async def event_generator():
        abort_event = asyncio.Event()
        accumulated_text = ""
        
        try:
            tools = get_tools()
            llm = create_llm(req.model, req.endpoint, req.is_local, req.api_key)
            
            agent_permission = agent_info.permission if agent_info else {}
            logger.info(f"[AGENT] Running {req.agent} in streaming mode")

            system_prompt = ctx_engine.build_system_prompt(agent_info)
            history_messages = ctx_engine.format_history_from_list(history)

            messages = [SystemMessage(content=system_prompt)]
            messages.extend(history_messages)
            messages.append(HumanMessage(content=req.query))
            messages = ctx_engine.truncate_if_needed(messages)

            logger.info(f"[MODEL_INPUT] Request: {req.query[:200]}... (messages: {len(messages)})")

            yield sse_event("start", {
                "session_id": session_id,
                "model": req.model,
                "agent": req.agent
            })
            
            yield sse_event("thought", {"text": "Processing request..."})
            
            last_heartbeat = time.time()
            max_iterations = 30
            iteration = 0
            
            while iteration < max_iterations:
                if abort_event.is_set():
                    yield sse_event("abort", "Request cancelled")
                    break
                
                if time.time() - last_heartbeat > 25:
                    yield sse_heartbeat()
                    last_heartbeat = time.time()
                
                iteration += 1
                logger.info(f"[ITERATION] {iteration}/{max_iterations}")
                
                try:
                    llm_with_tools = llm.bind_tools(tools)
                    response = await asyncio.to_thread(llm_with_tools.invoke, messages)
                    
                    tool_calls = getattr(response, 'tool_calls', None) or []
                    
                    if tool_calls:
                        for tc in tool_calls:
                            tool_name = tc.get('name', '')
                            tool_args = tc.get('args', {})
                            tool_call_id = tc.get('id', '')
                            
                            yield sse_event("tool-start", {
                                "tool": tool_name,
                                "args": tool_args,
                                "call_id": tool_call_id
                            })
                            
                            is_allowed, status = PermissionChecker.check(tool_name, tool_args, {})
                            if not is_allowed:
                                result = f"Permission denied: {tool_name}"
                                yield sse_event("tool-end", {
                                    "tool": tool_name,
                                    "call_id": tool_call_id,
                                    "result": result,
                                    "error": "permission_denied"
                                })
                                messages.append(response)
                                messages.append(ToolMessage(content=result, tool_call_id=tool_call_id))
                                continue
                            
                            if status == "ask":
                                result = f"Permission needed: {tool_name} requires confirmation"
                                yield sse_event("tool-end", {
                                    "tool": tool_name,
                                    "call_id": tool_call_id,
                                    "result": result,
                                    "status": "pending_confirmation"
                                })
                                messages.append(response)
                                messages.append(ToolMessage(content=result, tool_call_id=tool_call_id))
                                continue
                            
                            tool_obj = next((t for t in tools if t.name == tool_name), None)
                            if tool_obj:
                                try:
                                    result = tool_obj.invoke(tool_args)
                                    logger.info(f"[TOOL_RESULT] {tool_name}: {str(result)[:200]}...")
                                    yield sse_event("tool-end", {
                                        "tool": tool_name,
                                        "call_id": tool_call_id,
                                        "result": str(result)[:500],
                                        "status": "completed"
                                    })
                                    messages.append(response)
                                    messages.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))
                                except Exception as e:
                                    error_msg = f"Error: {e}"
                                    logger.error(f"[TOOL_ERROR] {tool_name}: {e}")
                                    yield sse_event("tool-end", {
                                        "tool": tool_name,
                                        "call_id": tool_call_id,
                                        "result": error_msg,
                                        "error": str(e)
                                    })
                                    messages.append(response)
                                    messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id))
                            else:
                                error_msg = f"Tool not found: {tool_name}"
                                yield sse_event("tool-end", {
                                    "tool": tool_name,
                                    "call_id": tool_call_id,
                                    "result": error_msg,
                                    "error": "tool_not_found"
                                })
                                messages.append(response)
                                messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call_id))
                        
                        yield sse_event("tool-loop-complete", {"iteration": iteration})
                        continue
                    
                    output = getattr(response, 'content', '') or ""
                    if output:
                        yield sse_event("text-delta", {"text": output})
                        accumulated_text += output
                    
                    yield sse_event("final-answer", {
                        "content": output,
                        "iteration": iteration
                    })
                    
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    retry_reason = RetryHandler.is_retryable(e)
                    
                    if retry_reason:
                        delay = RetryHandler.calculate_delay(iteration, e)
                        logger.warning(f"[RETRY] {retry_reason}, waiting {delay:.1f}s...")
                        yield sse_event("retry", {
                            "reason": retry_reason,
                            "delay": delay,
                            "attempt": iteration
                        })
                        
                        await asyncio.sleep(min(delay, 10))
                        continue
                    
                    logger.error(f"[ERROR] {error_msg}")
                    yield sse_event("error", {"message": error_msg, "type": type(e).__name__})
                    break
            
            if iteration >= max_iterations:
                yield sse_event("max-iterations", {"iterations": max_iterations, "accumulated": accumulated_text})

            new_messages = history + [
                {"role": "user", "content": req.query},
                {"role": "assistant", "content": accumulated_text}
            ]
            StorageManager.set(f"session:{session_id}", {
                "id": session_id,
                "messages": new_messages[-MAX_MESSAGES:],
                "updated_at": time.time()
            })
            logger.info(f"[SESSION] Saved {len(new_messages[-MAX_MESSAGES:])} messages")

            yield sse_event("complete", {"session_id": session_id})
            
        except asyncio.CancelledError:
            logger.info("[REQUEST] Request cancelled")
            abort_event.set()
            yield sse_event("abort", "Request was cancelled")
        except Exception as e:
            logger.error(f"[ERROR] {e}")
            try:
                yield sse_event("error", {"message": str(e), "type": type(e).__name__})
            except:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/agent/abort")
async def abort_agent(session_id: str = None):
    return {"status": "aborted", "session_id": session_id}


@router.get("/health")
async def health():
    tools = get_tools()
    return {
        "status": "ok",
        "tools": [t.name for t in tools],
        "context_engine": {
            "max_tokens": MAX_TOKENS,
            "max_messages": MAX_MESSAGES,
            "mode": "Streaming"
        },
        "version": "2.0"
    }


@router.get("/agents")
async def list_agents():
    agents = []
    for agent in AgentRegistry.list():
        agents.append({
            "name": agent.name,
            "description": agent.description,
            "mode": agent.mode.value,
            "native": agent.native,
        })
    return {"agents": agents}


@router.post("/permission/confirm")
async def confirm_permission(request: dict):
    from backend.permission.permission_manager import PermissionManager
    
    pending_id = request.get("pending_id")
    allow = request.get("allow", False)
    
    if not pending_id:
        return {"error": "pending_id required"}
    
    confirmed = PermissionManager.confirm(pending_id, allow)
    
    return {
        "confirmed": confirmed,
        "message": "Command executed" if confirmed else "Command denied"
    }


@router.get("/permission/pending")
async def list_pending():
    from backend.permission.permission_manager import PermissionManager
    
    PermissionManager.cleanup_expired()
    
    from dataclasses import asdict
    
    pending = []
    for p in PermissionManager._pending.values():
        pending.append({
            "id": p.id,
            "command": p.command,
            "warning": asdict(p.warning),
            "created_at": p.created_at
        })
    
    return {"pending": pending}


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    session = StorageManager.get(f"session:{session_id}")
    if session:
        return {"history": session.get("messages", [])}
    return {"history": []}


@router.get("/sessions")
async def list_sessions():
    sessions = []
    for key in StorageManager.list("session:"):
        session = StorageManager.get(key)
        if session:
            messages = session.get("messages", [])
            sessions.append({
                "id": session.get("id", key.replace("session:", "")),
                "message_count": len(messages),
                "last_message": messages[-1]["content"][:100] if messages else "",
                "updated_at": session.get("updated_at", 0)
            })
    return {"sessions": sessions}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    StorageManager.delete(f"session:{session_id}")
    return {"status": "deleted", "session_id": session_id}


@router.get("/project/info")
async def get_project_info(directory: str = None):
    project_dir = directory or os.getcwd()
    info = ProjectManager.get_info(project_dir)
    return info


@router.get("/project/files")
async def get_project_files(directory: str = None, pattern: str = "*"):
    project_dir = directory or os.getcwd()
    instance = ProjectManager.load(project_dir)
    import fnmatch
    files = [f for f in instance.state.files if fnmatch.fnmatch(f, pattern)]
    return {"files": files[:100], "total": len(files)}


@router.get("/models")
async def list_models(provider: str = None):
    from backend.provider.provider_manager import PROVIDER_MODELS, ModelInfo
    
    if provider:
        models = PROVIDER_MODELS.get(provider, [])
        return {
            "provider": provider, 
            "models": [{"id": m.id, "name": m.name, "context_length": m.context_length} for m in models]
        }

    all_models = []
    for p, models in PROVIDER_MODELS.items():
        for m in models:
            all_models.append({
                "id": m.id, 
                "name": m.name, 
                "provider": p, 
                "context_length": m.context_length,
                "supports_streaming": m.supports_streaming
            })

    return {"models": all_models, "providers": list(PROVIDER_MODELS.keys())}


@router.get("/vcs/status")
async def get_vcs_status(directory: str = None):
    project_dir = directory or os.getcwd()
    try:
        status = GitClient.status(project_dir)
        branch = GitClient.branch(project_dir)
        is_repo = GitClient.is_repo(project_dir)
        return {"is_repo": is_repo, "branch": branch, "status": status}
    except GitError as e:
        return {"error": str(e)}


@router.get("/vcs/diff")
async def get_vcs_diff(directory: str = None, file: str = None):
    project_dir = directory or os.getcwd()
    try:
        diff = GitClient.diff(project_dir, file)
        return {"diff": diff}
    except GitError as e:
        return {"error": str(e)}


@router.get("/vcs/log")
async def get_vcs_log(directory: str = None, limit: int = 10):
    project_dir = directory or os.getcwd()
    try:
        commits = GitClient.log(project_dir, limit)
        return {"commits": [{"hash": c.hash[:8], "message": c.message, "author": c.author, "timestamp": c.timestamp} for c in commits]}
    except GitError as e:
        return {"error": str(e)}


@router.get("/mcp/servers")
async def list_mcp_servers(directory: str = None):
    project_dir = directory or os.getcwd()
    MCPClient.initialize(project_dir)
    servers = MCPClient.list()
    return {"servers": [{"name": s.name, "command": s.command, "status": s.status.value, "tools_count": len(s.tools)} for s in servers]}


@router.get("/skills")
async def list_skills(directory: str = None):
    project_dir = directory or os.getcwd()
    SkillRegistry.initialize(project_dir)
    skills = SkillRegistry.list()
    return {"skills": [{"name": s.name, "description": s.description, "tools": s.tools} for s in skills]}


@router.post("/patch/create")
async def create_patch(description: str = "Manual patch"):
    patch_id = PatchManager.create_patch(description)
    return {"patch_id": patch_id}


@router.get("/patch/list")
async def list_patches():
    patches = PatchManager.list()
    return {"patches": patches}


@router.post("/patch/revert")
async def revert_patch(patch_id: str = None, dry_run: bool = False):
    result = PatchManager.revert(patch_id, dry_run)
    return result