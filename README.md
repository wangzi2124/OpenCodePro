# OpenCode Pro

基于 OpenCode 官方 (anomalyco/opencode) vscode-v0.0.13 分支重构的 AI 编程助手。

## 快速开始

### 前端

```bash
npm install
npm run dev
```

访问 http://localhost:5173

### 后端

```bash
cd backend
pip install -r requirements.txt
python main.py
```

后端运行在 http://localhost:3001

---

## 系统架构

### 业务流程

```
用户请求 → routes/proxy.py → LLM (ReAct循环) → Tools → SSE流式响应
                ↓
         SessionManager (对话历史)
         ProjectManager (项目上下文)
         PermissionManager (权限检查)
         StorageManager (数据持久化)
```

### 模块依赖关系

```
main.py
  └── __init__.py (FastAPI app)
        ├── routes/proxy.py (核心调度器)
        │     ├── AgentRegistry → agent/agent_def.py
        │     ├── get_tools() → tools/chain_tools.py
        │     ├── ContextEngine → project/project_manager.py
        │     ├── create_llm() → provider/provider_manager.py
        │     └── PermissionChecker → permission/permission_manager.py
        │
        ├── session/session_manager.py
        ├── storage/storage_manager.py
        ├── project/project_manager.py
        ├── provider/provider_manager.py
        ├── vcs/git_client.py
        ├── mcp/mcp_client.py
        └── retry/retry_manager.py
```

---

## 模块详解

### 核心模块

| 模块 | 文件 | 职责 | 关键类/函数 |
|------|------|------|-------------|
| **入口** | `main.py` | FastAPI + Uvicorn 启动 | - |
| **调度器** | `routes/proxy.py` | 请求路由、SSE流式、ReAct循环 | `AgentRequest`, `ContextEngine`, `sse_event()` |
| **Agent定义** | `agent/agent_def.py` | Agent注册、权限检查 | `AgentRegistry`, `PermissionChecker` |
| **Agent提示词** | `agent/prompts.py` | 各Agent系统提示词 | `GENERATE_PROMPT`, `EXPLORE_PROMPT` |
| **工具集** | `tools/chain_tools.py` | LangChain工具实现 | `read_file`, `write_file`, `edit_file`, `run_bash` |

### 支持模块

| 模块 | 文件 | 职责 | 关键类 |
|------|------|------|--------|
| **模型层** | `provider/provider_manager.py` | LLM调用、缓存、重试 | `LLMCache`, `RetryHandler`, `OpenAIProvider` |
| **会话管理** | `session/session_manager.py` | 对话历史存储 | `Session`, `SessionManager` |
| **权限管理** | `permission/permission_manager.py` | 危险命令检测 | `PermissionManager`, `CommandWarning` |
| **项目分析** | `project/project_manager.py` | 项目上下文加载 | `ProjectManager`, `ProjectState` |
| **数据存储** | `storage/storage_manager.py` | SQLite持久化 | `StorageManager`, `CacheManager` |
| **Git操作** | `vcs/git_client.py` | Git状态/diff/log | `GitClient`, `GitCommit` |
| **MCP协议** | `mcp/mcp_client.py` | MCP服务器连接 | `MCPClient`, `MCPServer` |
| **重试机制** | `retry/retry_manager.py` | 指数退避重试 | `RetryManager`, `RetryConfig` |

---

## 核心流程详解

### 1. 请求入口 (`/api/agent/run`)

```python
# routes/proxy.py
@router.post("/agent/run")
async def run_agent(req: AgentRequest):
    # 1. 加载会话历史
    history = req.history or StorageManager.get(f"session:{session_id}")
    
    # 2. 构建上下文
    ctx_engine = ContextEngine(req)
    system_prompt = ctx_engine.build_system_prompt(agent_info)
    
    # 3. 创建LLM实例
    llm = create_llm(req.model, req.endpoint, req.is_local)
    llm_with_tools = llm.bind_tools(tools)
    
    # 4. ReAct循环执行
    async for event in stream_llm_response(llm, tools, messages):
        yield sse_event(...)
```

### 2. LLM缓存策略 (`provider_manager.py`)

```python
class LLMCache:
    _llm_instances: Dict[str, ChatOpenAI] = {}  # 按provider+model+endpoint缓存
    _max_cache_size = 10  # 最多10个实例
    _last_used: Dict[str, float] = {}  # LRU淘汰时间戳
    
    @classmethod
    def get(cls, provider, model, base_url):
        key = f"{provider}|{model}|{base_url}"
        if key in cls._llm_instances:
            cls._last_used[key] = time.time()  # 更新访问时间
            return cls._llm_instances[key]
        return None
```

### 3. 权限检查 (`permission_manager.py`)

```python
class PermissionChecker:
    @staticmethod
    def check(tool_name, args, permission):
        # 1. edit权限: write_file, edit_file, batch_edit
        # 2. bash权限: glob模式匹配 (*, rm*, git*)
        # 3. skill权限: skill_invoke
        # 4. web权限: fetch_url, web_search
```

### 4. 工具执行 (`tools/chain_tools.py`)

```python
@tool
def read_file(file_path: str, offset: int = 0, limit: int = 2000):
    """读取文件，支持行号范围"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return "\n".join(f"{i+1}: {lines[i]}" ...)

@tool
def run_bash(command: str, workdir: str = None, timeout: int = 120):
    """执行命令，集成PermissionManager"""
    warning = PermissionManager.check_command(command)
    if warning.danger_level == DangerLevel.SAFE:
        return _execute_command(command, workdir, timeout)
```

### 5. 重试机制 (`provider_manager.py`)

```python
class RetryHandler:
    RETRY_INITIAL_DELAY = 2.0      # 初始延迟2秒
    RETRY_BACKOFF_FACTOR = 2        # 指数退避因子
    RETRY_MAX_DELAY = 30.0          # 最大延迟30秒
    
    @staticmethod
    def is_retryable(error):
        # 检测: Overloaded, rate_limit, server_error
        ...
    
    @staticmethod
    def calculate_delay(attempt, error=None, headers=None):
        # 优先读取 retry-after-ms 头
        # 否则: delay = 2 * 2^(attempt-1)
```

---

## SSE 事件流

```
连接建立 → start (session_id, model, agent)
     ↓
thought (Processing request...)
     ↓
工具调用循环:
  tool-start (tool_name, args)
  tool-end (result, status)
  tool-loop-complete (iteration)
     ↓
text-delta (实时文本片段)
     ↓
final-answer (完整回复)
     ↓
complete (会话结束)
     ↓
heartbeat (每25秒保活)
```

### 事件类型

| 事件 | data | 说明 |
|------|------|------|
| `start` | `{session_id, model, agent}` | 会话开始 |
| `thought` | `{text}` | AI思考 |
| `tool-start` | `{tool, args, call_id}` | 工具开始 |
| `tool-end` | `{tool, result, status}` | 工具结束 |
| `text-delta` | `{text}` | 文本片段 |
| `final-answer` | `{content, iteration}` | 最终答案 |
| `heartbeat` | `{}` | 25s保活 |
| `retry` | `{reason, delay, attempt}` | 重试中 |
| `error` | `{message, type}` | 错误 |
| `complete` | `{session_id}` | 流结束 |

---

## Agent 系统

| Agent | 权限 | 提示词 |
|-------|------|--------|
| `build` | edit✅ bash✅ web✅ | 通用开发 |
| `plan` | edit❌ bash⚠️ web✅ | 只读分析 |
| `explore` | edit❌ bash❌ web✅ | 快速探索 |
| `general` | edit✅ bash✅ web✅ | 通用研究 |

### 权限模式

- `Permission.ALLOW` - 允许执行
- `Permission.DENY` - 拒绝执行
- `Permission.ASK` - 需用户确认

---

## 可用工具

| 工具 | 功能 | 参数 |
|------|------|------|
| `read_file` | 读取文件 | `file_path`, `offset=0`, `limit=2000` |
| `write_file` | 创建文件 | `file_path`, `content` |
| `edit_file` | 编辑文件 | `file_path`, `old_string`, `new_string` |
| `glob_search` | 文件匹配 | `pattern`, `path="."` |
| `grep_search` | 内容搜索 | `pattern`, `include="*"`, `path="."` |
| `run_bash` | 执行命令 | `command`, `workdir`, `timeout=120` |
| `fetch_url` | HTTP获取 | `url` |
| `create_vite_project` | 脚手架 | `directory`, `template`, `name` |
| `install_dependencies` | npm安装 | `directory` |

---

## 技术栈

### 前端
- React 18 + Vite 5
- Zustand (状态管理)
- SSE 流式渲染

### 后端
- FastAPI + Uvicorn
- LangChain (Ollama / OpenAI / Anthropic)
- SQLite (数据持久化)

---

## 命令

```bash
# 前端
npm run dev      # 开发服务器 (5173)
npm run build    # 生产构建

# 后端
python backend/main.py  # API 服务 (3001)
```

---

## Windows 注意事项

- 创建目录: `New-Item -ItemType Directory -Path "folder"`
- 避免 `&&`，使用分号或分别运行命令
- 使用 `curl.exe` 而非 `curl` 别名