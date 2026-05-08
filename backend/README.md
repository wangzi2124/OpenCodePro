# OpenCode Pro Backend

FastAPI backend with built-in ReAct Agent.

## Structure

```
backend/
├── main.py              # FastAPI entry point
├── requirements.txt
└── routes/
    └── proxy.py         # ReActAgent + single /agent/run endpoint

tools/                   # Independent tool package
├── __init__.py
├── registry.py          # ToolRegistry class
├── file_tools.py        # read_file, write_file, edit_file
├── search_tools.py      # glob_search, grep_search
├── bash_tools.py        # run_bash
└── web_tools.py         # fetch_url, web_search, code_search
```

## Setup

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file with:
```
OPENROUTER_API_KEY=your-key-here
```

## Run

```bash
cd backend
python main.py
```

Server runs at `http://localhost:3001`.

## API Endpoints

- `POST /api/agent/run` - ReAct Agent execution (唯一入口)
- `GET /api/health` - Health check + tool list

## Agent Pattern (ReAct)

内置 `ReActAgent` 类，基于参考实现：

1. **Thought** - `<thought>` LLM 分析任务
2. **Action** - `<action>tool_name(args)</action>` 调用工具
3. **Observation** - `<observation>result</observation>` 工具结果反馈
4. **Loop** - 循环直到 `<final_answer>`

工具通过 `ToolRegistry` 自动注册，函数签名和文档字符串动态注入系统提示。

## Request Example

```json
POST /api/agent/run
{
  "query": "读取 package.json 并告诉我项目名称",
  "model": "openai/gpt-4o",
  "api_key": "sk-xxx (可选)",
  "project_directory": "D:\\project\\my-app",
  "max_iterations": 15
}
```

## Response Example

```json
{
  "success": true,
  "final_answer": "项目名称是 my-app",
  "thoughts": ["需要读取 package.json...", "已获取内容，提取名称"],
  "actions": ["read_file(\"D:\\\\project\\\\my-app\\\\package.json\")"],
  "observations": ["{\"name\": \"my-app\", ...}"]
}
```
