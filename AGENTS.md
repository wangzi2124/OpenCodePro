# AGENTS.md - OpenCode Pro

Based on OpenCode official (anomalyco/opencode) vscode-v0.0.13.

## Commands

```powershell
# Frontend
npm run dev    # Development (port 5173, proxy /api to 3001)
npm run build  # Production build

# Backend (run in separate terminal)
cd backend
pip install -r requirements.txt
python main.py  # Port 3001
```

## Project Structure

```
src/                      # React + Vite frontend
├── components/           # ChatArea, Sidebar, AgentPanel, Terminal
├── store/chatStore.js    # SSE streaming + state management
└── styles/               # CSS

backend/                  # FastAPI backend
├── routes/proxy.py       # SSE streaming agent endpoint
├── provider/             # LLM providers + RetryHandler
└── tools/chain_tools.py  # LangChain tools
```

## SSE Events (Streaming)

| Event | 说明 |
|-------|------|
| `start` | Session started |
| `thought` | AI thinking |
| `tool-start` | Tool execution started |
| `tool-end` | Tool execution completed |
| `text-delta` | Streaming text output |
| `final-answer` | Final response |
| `heartbeat` | 25s keepalive ping |
| `retry` | API retry with delay |
| `error` | Error occurred |
| `complete` | Stream finished |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/agent/run` | POST | Run agent (SSE streaming) |
| `/api/agents` | GET | List agents |
| `/api/health` | GET | Health check |
| `/api/models` | GET | List available models |

## Request Format

```json
{
  "query": "task description",
  "model": "qwen2.5:latest",
  "endpoint": "http://localhost:11434",
  "is_local": true,
  "agent": "build",
  "session_id": "uuid",
  "history": [{"role": "user", "content": "..."}]
}
```

## Agents

| Agent | Permission | Mode |
|-------|-----------|------|
| `build` | Full edit/bash | Streaming ReAct |
| `plan` | Read-only | Streaming ReAct |
| `explore` | No edit/bash | Streaming ReAct |
| `general` | Full access | Streaming ReAct |

## Backend Streaming Implementation

- Uses `StreamingResponse` with async generator for true SSE streaming
- Every 25s sends heartbeat to prevent connection timeout
- Tool execution sends `tool-start` → `tool-end` events
- Text streaming via `text-delta` events for real-time output
- `RetryHandler` with exponential backoff (2s → 30s max)

## Key Implementation Details

1. **LLM Cache**: `backend/provider/provider_manager.py` - `LLMCache` class caches LLM instances by provider+model+endpoint hash
2. **Retry**: Detects "Overloaded", "rate_limit", "server_error" and respects `retry-after-ms` headers
3. **Session**: Stored in `StorageManager` with max 20 messages (MAX_MESSAGES)
4. **Context**: Auto-loads project files + dependencies for context engineering

## Testing

```bash
# Health check
Invoke-WebRequest -Uri http://localhost:3001/api/health -Method GET

# Agent run (PowerShell)
$body = @{query="list files"; model="qwen2.5:latest"; is_local=$true} | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:3001/api/agent/run -Method POST -Body $body -ContentType "application/json"
```