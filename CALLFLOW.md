# OpenCode Pro 技术文档 - 代码调用流程

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      前端 (React + Vite)                    │
│                                                             │
│  ChatArea ──sendMessage()──▶ chatStore ──fetch()──▶ AgentPanel │
└────────────────────────────┬──────────────────────────────────────┘
                         │ POST /api/agent/run
                         ▼
┌───────────────────────────────────────────────────────────────────────┐
│                   后端 (FastAPI)                       │
│                                                      │
│  routes/proxy.py                                        │
│  ├── get_langchain_tools() ──▶ chain_tools.py           │
│  ├── AgentRegistry ──▶ agent/agent_def.py         │
│  └── ReActAgentWrapper ──▶ tool.invoke()        │
└───────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────┐
│              LLM (Ollama / OpenRouter)               │
└──────────────────────────────────────────────────────┘
```

---

## 前端调用流程

### 1. 用户输入 (ChatArea.jsx)

```
用户输入 ──▶ onSubmit ──▶ chatStore.sendMessage(content)
```

### 2. 发送请求 (chatStore.js:60-97)

```javascript
// 1. 构建请求参数
const query = ragContext ? `${ragContext}\n\n${content}` : content
const body = {
  query: query,           // 用户问题
  model: 'qwen2.5:latest', // 模型 ID
  api_key: apiKey,       // API Key
  endpoint: endpointUrl,  // API 端点
  is_local: true,        // 是否本地模型
  agent: 'build'        // Agent 名称
}

// 2. 发送 SSE 请求
const res = await fetch('/api/agent/run', {
  method: 'POST',
  body: JSON.stringify(body)
})
```

### 3. 解析 SSE 响应 (chatStore.js:99-162)

```javascript
// 逐行解析 SSE 事件
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  
  buffer += decoder.decode(value, { stream: true })
  const events = buffer.split('\n\n')
  
  for (const evt of events) {
    const event = JSON.parse(evt.slice(6))  // 去掉 "data: "
    const { type, data } = event
    
    // 处理不同类型事件
    if (type === 'thought')      steps.push(data)
    if (type === 'action')      steps.push(data)
    if (type === 'observation') steps.push(data)
    if (type === 'final_answer') // 完成
  }
}
```

### SSE 事件类型

| 事件类型 | 说明 | 示例数据 |
|---------|------|---------|
| `thought` | 模型思考过程 | "正在分析用户请求..." |
| `action` | 调用的工具 | "glob_search" |
| `observation` | 工具执行结果 | 文件列表 |
| `final_answer` | 最终答案 | "已完成..." |
| `error` | 错误信息 | "Error: ..." |

---

## 后端调用流程

### 入口 (routes/proxy.py:342-360)

```python
@router.post("/agent/run")
async def run_agent(req: AgentRunRequest):
    # 1. 获取 Agent 配置
    agent_info = AgentRegistry.get(req.agent)
    
    # 2. 获取工具列表
    tools = get_langchain_tools()
    
    # 3. 创建 Agent 并运行
    agent_class = get_agent_class(req.model, req.endpoint, req.is_local)
    agent = agent_class(tools=tools, model=req.model, ...)
    
    # 4. SSE 流式返回
    for event_type, event_data in agent.run_stream(req.query):
        yield sse_event({"type": event_type, "data": event_data})
```

### ReAct Agent 核心逻辑 (proxy.py:380-456)

```python
class ReActAgentWrapper:
    def run_stream(self, user_input):
        # 1. 构建系统提示
        system_prompt = f"""You are an AI coding assistant.
        
Available tools:
- read_file: 读取文件
- write_file: 写入文件
- glob_search: 文件搜索
...

Format:
<tool_call>
tool_name | param="value"
</tool_call>"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        # 2. 循环调用 LLM
        for i in range(max_iterations=10):
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
            )
            content = resp.choices[0].message.content
            
            # 3. 解析工具调用
            tool_match = re.search(r"<tool_call>\s*(\w+)\s*\|", content)
            final_match = re.search(r"final_answer\s*\|\s*result=\"([^\"]+)\"", content)
            
            # 4. 返回最终答案
            if final_match:
                yield ("final_answer", final_match.group(1))
                return
            
            # 5. 执行工具
            if tool_match:
                tool_name = tool_match.group(1)
                tool = self.tool_map.get(tool_name)
                
                # 解析参数
                args_dict = parse_args(content)
                
                # 执行工具
                result = tool.invoke(args_dict)
                
                # 6. 返回观察结果，继续循环
                yield ("observation", str(result))
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"<observation>{result}</observation>"})
                continue
            
            # 7. 无工具调用，返回结果
            yield ("final_answer", content or "Done")
            return
```

### ReAct 模式流程图

```
┌────────────────────────────────────────┐
│           User Query                     │
│    "list files in src"                   │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│      LLM (with tools)                   │
│                                        │
│  Output: <tool_call>                   │
│  glob_search | path="src/*"             │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌──────────────��─────────────────────────┐
│      Execute Tool                       │
│                                        │
│  result = glob_search(path="src/*")      │
│  = ["src/App.jsx", "src/components/"] │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│      Yield observation                │
│                                        │
│  "src/App.jsx\nsrc/components/..."     │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│      LLM (with observation)            │
│                                        │
│  Output: <tool_call>                   │
│  final_answer | result="Files: ..."     │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│           Done                         │
└────────────────────────────────────────┘
```

---

## 工具系统

### 工具定义 (chain_tools.py)

```python
from langchain.tools import tool

@tool
def glob_search(pattern: str, path: str = ".") -> str:
    """Fast file pattern matching tool."""
    import glob
    matches = glob.glob(os.path.join(path, pattern), recursive=True)
    return "\n".join(matches)
```

### 工具注册 (get_langchain_tools)

```python
def get_langchain_tools():
    from tools.chain_tools import TOOL_REGISTRY
    return TOOL_REGISTRY  # [read_file, write_file, ...]
```

### 可用工具

| 工具 | 描述 | 参数 |
|------|------|------|
| `read_file` | 读取文件 | file_path, offset, limit |
| `write_file` | 写入文件 | file_path, content |
| `edit_file` | 编辑文件 | file_path, old_string, new_string |
| `glob_search` | 文件搜索 | pattern, path |
| `grep_search` | 内容搜索 | pattern, include, path |
| `run_bash` | 执行命令 | command, workdir, timeout |
| `fetch_url` | 获取网页 | url |
| `web_search` | 网络搜索 | query |
| `agent_kill` | 终止执行 | - |

---

## Agent 系统

### Agent 定义 (agent_def.py)

```python
@dataclass
class AgentInfo:
    name: str           # build/plan/explore/general
    mode: AgentMode   # primary/subagent
    permission: Dict  # 权限配置
    tools: Dict     # 工具配置
```

### 内置 Agent

```python
AgentRegistry._agents = {
    "build": AgentInfo(
        name="build",
        mode=AgentMode.PRIMARY,
        permission={"edit": "allow", "bash": {"*": "allow"}},
    ),
    "plan": AgentInfo(
        name="plan", 
        mode=AgentMode.PRIMARY,
        permission={"edit": "deny", "bash": {"*": "deny"}},
    ),
    "explore": AgentInfo(...),
    "general": AgentInfo(...),
}
```

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agent/run` | POST | 运行 Agent |
| `/api/agents` | GET | 列出 Agent |
| `/api/health` | GET | 健康检查 |

---

## 完整调用示例

### 请求

```bash
curl -X POST http://localhost:3001/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{"query": "list files in src", "model": "qwen2.5:latest", "agent": "build", "is_local": true}'
```

### SSE 响应流

```
data: {"type": "thought", "data": "Analyzing request..."}

data: {"type": "action", "data": "glob_search"}

data: {"type": "observation", "data": "src/App.jsx\nsrc/components/..."}

data: {"type": "final_answer", "data": "Based on the file listing..."}
```

---

## 关键文件

| 文件 | 职责 |
|------|------|
| `src/store/chatStore.js` | 聊天状态 + SSE 解析 |
| `src/components/ChatArea.jsx` | 聊天界面 |
| `backend/routes/proxy.py` | Agent API + ReAct 逻辑 |
| `backend/agent/agent_def.py` | Agent 定义 |
| `backend/tools/chain_tools.py` | 工具实现 |

---

## 调试日志

后端日志前缀：

- `[AGENT]` - Agent 选择信息
- `[OUTPUT N]` - LLM 响应
- `[TOOL]` - 工具调用
- `[RESULT]` - 工具结果
- `[ERROR]` - 错误信息