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
用户请求 → routes/proxy.py → ContextEngine → LLM → Tools → SSE 流式响应
                ↓
         SessionManager (对话历史)
         ProjectManager (项目上下文)
         PermissionManager (权限检查)
         StorageManager (数据持久化)
```

### 模块说明

| 模块 | 文件 | 职责 |
|------|------|------|
| **入口** | `main.py` | FastAPI + Uvicorn 启动 (端口 3001) |
| **路由** | `routes/proxy.py` | API 路由、SSE 流式响应、ReAct 循环执行 |
| **Agent** | `agent/agent_def.py` | Agent 定义 (build/plan/explore/general)、权限系统 |
| **工具** | `tools/chain_tools.py` | LangChain 工具集 (文件操作、命令执行等) |
| **模型** | `provider/provider_manager.py` | LLM 提供者、LLM 缓存、重试机制 |
| **会话** | `session/session_manager.py` | 对话历史管理、消息持久化 |
| **权限** | `permission/permission_manager.py` | 危险命令检测、用户确认 |
| **项目** | `project/project_manager.py` | 项目上下文加载、文件列表、依赖分析 |
| **存储** | `storage/storage_manager.py` | SQLite + 内存缓存、键值存储 |
| **MCP** | `mcp/mcp_client.py` | MCP 协议客户端、扩展工具连接 |
| **VCS** | `vcs/git_client.py` | Git 操作 (status/diff/log) |
| **重试** | `retry/retry_manager.py` | 指数退避重试策略 |

### 核心模块详解

#### routes/proxy.py - 核心调度器

- `AgentRequest`: 请求参数模型
- `ContextEngine`: 构建项目上下文
- `sse_event()`: SSE 事件格式化
- `/api/agent/run`: SSE 流式 Agent 执行

#### provider/provider_manager.py - 模型层

- `LLMCache`: LLM 实例缓存 (LRU, 最多 10 个)
- `RetryHandler`: API 重试 (Overloaded/rate_limit/server_error)
- 支持: Ollama / OpenAI / Anthropic

#### tools/chain_tools.py - 工具层

| 工具 | 功能 |
|------|------|
| `read_file` | 读取文件 (支持 offset/limit) |
| `write_file` | 创建新文件 |
| `edit_file` | 替换文件内容 |
| `glob_search` | 文件模式匹配 |
| `grep_search` | 内容正则搜索 |
| `run_bash` | 执行 Shell 命令 |
| `fetch_url` | HTTP 获取网页 |
| `create_vite_project` | Scaffolding 脚手架 |
| `install_dependencies` | npm 依赖安装 |

---

## 核心特性

### ReAct 循环模式

```
Thought: 分析问题
Action: read_file("src/main.py")
Observation: 文件内容...
Thought: 继续执行
→ text-delta (实时流式输出)
→ tool-start / tool-end (工具执行状态)
Final Answer: 完成
```

### SSE 实时事件

| 事件 | 说明 |
|------|------|
| `start` | 会话开始 |
| `thought` | AI 思考 |
| `tool-start` | 工具开始执行 |
| `tool-end` | 工具执行完成 |
| `text-delta` | 实时文本流 |
| `final-answer` | 最终答案 |
| `heartbeat` | 25s 保活心跳 |
| `retry` | API 重试中 |
| `error` | 错误发生 |
| `complete` | 流结束 |

### 权限系统

| Agent | edit | bash | webfetch |
|-------|------|------|----------|
| `build` | ✅ | ✅ | ✅ |
| `plan` | ❌ | ⚠️ 部分 | ✅ |
| `explore` | ❌ | ❌ | ✅ |
| `general` | ✅ | ✅ | ✅ |

### 模型缓存策略

```
请求 → LLMCache 检查
  ├─ 命中: 返回缓存实例
  └─ 未命中: 创建新实例 (最多 10 个)
              → LRU 淘汰最旧实例
```

### 重试机制

- **检测错误**: Overloaded, rate_limit, server_error, exhausted
- **退避策略**: 指数退避 (2s → 4s → 8s → ... → 30s 上限)
- **Header 支持**: 读取 `retry-after-ms` / `retry-after`

---

## 内置 Agent

| Agent | 模式 | 说明 |
|-------|------|------|
| `build` | ReAct | 全功能开发 Agent |
| `plan` | ReAct | 只读分析 Agent |
| `explore` | ReAct | 快速代码探索 |
| `general` | ReAct | 通用研究任务 |
| `compaction` | Hidden | 上下文压缩 |
| `title` | Hidden | 标题生成 |
| `summary` | Hidden | 摘要生成 |

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agent/run` | POST | 运行 Agent (SSE 流式) |
| `/api/agents` | GET | 列出所有 Agent |
| `/api/health` | GET | 健康检查 |
| `/api/models` | GET | 列出可用模型 |
| `/api/session/{id}/history` | GET | 获取会话历史 |
| `/api/sessions` | GET | 列出所有会话 |
| `/api/permission/pending` | GET | 待确认权限 |
| `/api/project/info` | GET | 项目信息 |

### 请求格式

```json
{
  "query": "任务描述",
  "model": "qwen2.5:latest",
  "endpoint": "http://localhost:11434",
  "is_local": true,
  "agent": "build",
  "session_id": "uuid",
  "history": [{"role": "user", "content": "..."}]
}
```

---

## 模型配置

### 本地模型 (Ollama)

```bash
ollama serve
ollama pull qwen2.5:latest
```

### 云端模型 (OpenRouter)

- Endpoint: `https://openrouter.ai/api/v1`
- API Key: `sk-or-v1-...`

推荐模型：
| 模型 | ID |
|------|-----|
| Kimi K2.5 | `moonshotai/kimi-k2.5` |
| GPT-4o | `openai/gpt-4o` |
| Claude 3.5 | `anthropic/claude-3.5-sonnet` |

---

## 技术栈

### 前端
- React 18 + Vite 5
- Zustand (状态管理)
- SSE 流式渲染
- react-markdown

### 后端
- FastAPI + Uvicorn
- LangChain (Ollama / OpenAI / Anthropic)
- SQLite (数据持久化)
- ReAct 循环 + SSE 流式响应

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