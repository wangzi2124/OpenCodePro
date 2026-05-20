# OpenCode Pro

基于 [OpenCode](https://opencode.ai) (anomalyco/opencode) vscode-v0.0.13 重构的 AI 编程助手。

## 快速开始

### 前端

```bash
npm install
npm run dev      # 开发服务器 http://localhost:5173
npm run build    # 生产构建
```

### 后端

```bash
cd backend
pip install -r requirements.txt
python main.py   # API 服务 http://localhost:3001
```

---

## 系统架构

### 目录结构

```
src/                      # React + Vite 前端
├── components/           # ChatArea, Sidebar, AgentPanel, Terminal, Tetris
├── store/                # chatStore, modelStore, ragStore (Zustand)
└── styles/               # CSS (暗色主题)

backend/                  # FastAPI 后端
├── main.py               # Uvicorn 入口
├── __init__.py            # FastAPI app 创建 + 事件总线初始化
│
├── routes/
│   └── proxy.py          # SSE 流式 Agent 端点 + 事件总线SSE端点
│
├── agent/
│   ├── agent_def.py      # Agent 注册、权限检查
│   ├── prompts.py        # 提示词加载器 (从 .txt 文件加载)
│   └── prompts/          # Agent 提示词 .txt 文件 (5个)
│       ├── generate.txt, explore.txt
│       ├── compaction.txt, title.txt
│       └── summary.txt
│
├── session/
│   ├── session_manager.py
│   └── prompts/          # 模型专属系统提示词 .txt 文件 (7个)
│       ├── anthropic.txt, beast.txt, codex.txt
│       ├── gemini.txt, qwen.txt, plan.txt
│       └── build-switch.txt, max-steps.txt
│
├── command/
│   └── templates/        # 斜杠命令模板 .txt 文件
│       ├── initialize.txt, review.txt
│
├── tools/
│   ├── chain_tools.py    # 所有工具 (LangChain @tool)
│   ├── edit_replacer.py  # 8种替换策略
│   ├── ripgrep_util.py   # ripgrep 搜索引擎
│   ├── lsp_diagnostics.py
│   ├── file_time.py      # 读前编辑校验
│   └── prompts/          # 工具描述 .txt 文件 (17个)
│
├── provider/
│   └── provider_manager.py  # 12个提供商, 53个模型, LLM缓存, 重试
│
├── bus/
│   └── event_bus.py      # 事件总线 (发布/订阅 + SSE推送)
│
├── snapshot/
│   └── snapshot_manager.py # 文件快照 (diff/回退)
│
├── skill/
│   └── skill_def.py      # 7个内置技能
│
├── patch/
│   └── patch_manager.py  # 补丁追踪/回退
│
├── permission/
│   └── permission_manager.py # 危险命令检测
│
├── project/
│   └── project_manager.py
│
├── storage/
│   └── storage_manager.py # SQLite + 内存双写
│
├── vcs/
│   └── git_client.py
│
├── mcp/
│   ├── mcp_client.py     # MCP 协议客户端
│   └── mcp_full.py
│
├── auth/
│   └── auth_manager.py   # 认证系统
│
├── budget/
│   └── token_manager.py  # Token 预算/计费
│
├── share/
│   └── share_manager.py  # 会话分享
│
├── acp/
│   └── acp_client.py     # Agent Client Protocol
│
├── lsp/
│   └── lsp_client.py     # LSP 语言服务器客户端
│
├── config/
│   └── config_manager.py
└── retry/
    └── retry_manager.py
```

### 请求执行流程

```
Browser → POST /api/agent/run (SSE)
                    ↓
routes/proxy.py → ContextEngine.build_system_prompt()
                    ↓
            EventBus.publish(AGENT_START)
                    ↓
            create_llm() → LLM 实例 (有缓存)
                    ↓
            ReAct 循环 (最多30轮):
              LLM.invoke() → 有 tool_calls?
                ├─ 是 → 执行工具 → ToolMessage → 继续
                │    └─ task_delegate? → 启动子Agent → 合并结果
                └─ 否 → 输出 text-delta → final-answer
                    ↓
            EventBus.publish(AGENT_COMPLETE)
                    ↓
            StorageManager.save() → SQLite
```

---

## 提示词系统

采用 **独立 .txt 文件 + Python 加载器** 架构，与官方版一致。

### Agent 提示词 (`backend/agent/prompts/`)

| 文件 | 用途 |
|------|------|
| `generate.txt` | build agent - 代码生成 |
| `explore.txt` | explore agent - 代码探索 |
| `compaction.txt` | 上下文压缩/摘要 |
| `title.txt` | 对话标题生成 |
| `summary.txt` | 变更摘要生成 |

### 模型专属提示词 (`backend/session/prompts/`)

| 文件 | 适用模型 | 特点 |
|------|----------|------|
| `anthropic.txt` | Claude 系列 | 专业性、任务管理、工具策略 |
| `beast.txt` | GPT-4/o 系列 | 自主性、深度推理、互联网调研 |
| `codex.txt` | GPT-5/Codex | 精确规范、沙箱安全、代码风格 |
| `gemini.txt` | Google Gemini | 核心指令、主流程、安全规则 |
| `qwen.txt` | Qwen/Llama 等 | 简洁风格、安全约束、低token |
| `plan.txt` | 所有模型(Plan模式) | 只读分析、禁止修改 |
| `build-switch.txt` | 所有模型 | Plan→Build 模式切换指令 |

### 工具描述提示词 (`backend/tools/prompts/`)

每个工具一个 `.txt` 文件，供 LLM 理解工具用法。

---

## 提供商系统

| 提供商 | 模型数 | 支持工具 | 需要 API Key |
|--------|--------|---------|-------------|
| **Ollama** | 13 | ✅ | `OLLAMA_BASE_URL` (默认 localhost:11434) |
| **OpenAI** | 7 | ✅ | `OPENAI_API_KEY` |
| **Anthropic** | 4 | ✅ | `ANTHROPIC_API_KEY` |
| **OpenRouter** | 8 | ✅ | `OPENROUTER_API_KEY` |
| **Groq** | 4 | ✅ | `GROQ_API_KEY` |
| **Google Gemini** | 3 | ✅ | `GOOGLE_API_KEY` |
| **DeepSeek** | 2 | ✅ | `DEEPSEEK_API_KEY` |
| **Together AI** | 4 | ✅ | `TOGETHER_API_KEY` |
| **Perplexity** | 2 | - | `PERPLEXITY_API_KEY` |
| **xAI (Grok)** | 2 | ✅ | `XAI_API_KEY` |
| **DeepInfra** | 2 | ✅ | `DEEPINFRA_API_KEY` |
| **Mistral** | 2 | ✅ | `MISTRAL_API_KEY` |

所有 OpenAI 兼容的提供商通过 `OpenAICompatibleProvider` 统一接入。

---

## 工具系统

| 工具 | 功能 |
|------|------|
| `read_file` | 读取文件 (支持 offset/limit) |
| `write_file` | 创建/覆盖文件 |
| `edit_file` | 精确文本替换 (8种匹配策略) |
| `glob_search` | 文件通配符搜索 |
| `grep_search` | 正则内容搜索 |
| `run_bash` | Shell 命令执行 (含权限检查) |
| `fetch_url` | HTTP 网页获取 |
| `web_search` | 网络搜索 |
| `batch_edit` | 批量文件编辑 |
| `task_delegate` | 子 Agent 任务委派 |
| `task_status` | 查询子任务状态 |
| `codesearch` | 语义代码搜索 (关键词提取) |
| `multiedit` | 跨文件多编辑 |
| `lsp_diagnostics` | LSP 诊断查询 |
| `todo_read` | 读取任务列表 |
| `todo_write` | 更新任务列表 |
| `skill_list` | 列出技能 |
| `skill_invoke` | 调用技能 |

---

## 事件总线系统

全局事件总线，支持发布/订阅 + SSE 实时推送。

| 事件 | 触发时机 | data |
|------|---------|------|
| `agent.start` | Agent 开始执行 | `{session_id, model, agent, query}` |
| `agent.complete` | Agent 执行完成 | `{session_id, iterations}` |
| `agent.error` | Agent 执行出错 | `{session_id, error}` |
| `tool.start` | 工具开始执行 | `{tool, args, session_id}` |
| `tool.end` | 工具执行完成 | `{tool, status, session_id}` |
| `session.created` | 会话创建 | - |
| `system.startup` | 后端启动 | `{version}` |

订阅: `GET /api/events` (SSE)

---

## SSE 事件流

```
连接建立 → agent.start
    ↓
thought (Processing request...)
    ↓
工具调用循环:
  tool-start (tool, args)
  tool-end (result, status)
  tool-loop-complete (iteration)
    ↓
  (可选) task_delegate → 子Agent执行 → tool-end
    ↓
text-delta (实时文本)
    ↓
final-answer (完整回复)
    ↓
agent.complete
    ↓
complete (session_id)
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

| Agent | Edit | Bash | Web | 模式 |
|-------|------|------|-----|------|
| `build` | ✅ 允许 | ✅ 允许 | ✅ 允许 | 全功能开发 |
| `plan` | ❌ 禁止 | ⚠️ 仅安全命令 | ✅ 允许 | 只读分析 |
| `explore` | ❌ 禁止 | ❌ 禁止 | ✅ 允许 | 代码探索 |
| `general` | ✅ 允许 | ✅ 允许 | ✅ 允许 | 通用研究 |

### 权限模式

- `ALLOW` - 允许执行
- `DENY` - 拒绝执行
- `ASK` - 需用户确认

---

## 快照系统

自动对文件写/编辑操作创建快照，支持 diff 和回退。

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/snapshot/take` | POST | 手动快照 |
| `/api/snapshot/diff` | GET | 对比变更 |
| `/api/snapshot/changed` | GET | 列出变更文件 |
| `/api/snapshot/revert` | POST | 回退文件 |
| `/api/snapshot/clear` | POST | 清除快照 |

---

## API 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/agent/run` | POST | 运行 Agent (SSE) |
| `/api/agent/abort` | POST | 取消请求 |
| `/api/events` | GET | 事件总线 SSE |
| `/api/agents` | GET | 列出 Agent |
| `/api/models` | GET | 列出模型 |
| `/api/health` | GET | 健康检查 |
| `/api/config` | GET | 配置信息 |
| `/api/sessions` | GET | 会话列表 |
| `/api/skills` | GET | 技能列表 |
| `/api/mcp/servers` | GET | MCP 服务器 |
| `/api/vcs/status` | GET | Git 状态 |
| `/api/vcs/diff` | GET | Git diff |
| `/api/project/info` | GET | 项目信息 |
| `/api/permission/pending` | GET | 待审批操作 |
| `/api/patch/list` | GET | 补丁列表 |
| `/api/snapshot/changed` | GET | 变更文件列表 |

---

## 技能系统

7 个内置技能 + 自定义技能 (`.opencode/skills/*.json`):

| 技能 | 用途 | 使用工具 |
|------|------|---------|
| `read` | 阅读代码 | read, glob, grep |
| `write` | 编写代码 | write, read, edit |
| `refactor` | 重构代码 | read, edit, glob |
| `debug` | 调试修复 | read, grep, bash |
| `test` | 编写测试 | write, read, bash |
| `explain` | 解释代码 | read, glob, grep |
| `review` | 代码审查 | read, grep |

---

## 技术栈

### 前端
- React 18 + Vite 5
- Zustand (状态管理)
- SSE 流式渲染
- Framer Motion (动画)

### 后端
- FastAPI + Uvicorn
- LangChain (Ollama / OpenAI / Anthropic / 12 providers)
- SQLite (数据持久化)
- 文件系统 KV 存储

---

## 环境变量

```bash
# 本地模型
OLLAMA_BASE_URL=http://localhost:11434

# 云端 API
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-...
TOGETHER_API_KEY=...
PERPLEXITY_API_KEY=...
XAI_API_KEY=...
DEEPINFRA_API_KEY=...
MISTRAL_API_KEY=...
```

---

## Windows 注意事项

- 创建目录: `New-Item -ItemType Directory -Path "folder"`
- 避免 `&&`，使用 `;` 或分别运行
- 使用 `curl.exe` 而非 `curl` 别名
