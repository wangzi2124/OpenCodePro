# AGENTS.md - OpenCode Pro

## Commands

```bash
npm run dev       # Dev server at http://localhost:5173
npm run build     # Build to dist/
npm run preview  # Preview production build
npm run server   # Tool API server (port 3001)
npm run start   # Run both dev + server
```

## Tech Stack

- React 18 + Vite 5
- Zustand (state)
- CSS variables (dark theme, GitHub-inspired)

## Project Structure

```
src/
├── components/   # Header, Sidebar, ChatArea, Terminal, AgentPanel, ModelModal, RAGPanel
├── store/         # Zustand stores (modelStore, agentStore, ragStore, chatStore)
├── types/        # Enums
├── styles/       # Global CSS
├── App.jsx       # Main entry
└── main.jsx      # React entry
```

## API Proxy (Critical)

Vite proxy forwards `/api` to Express (3001):
- `/api/proxy/ollama` → Ollama at `localhost:11434`
- `/api/proxy/openai` → OpenAI API

前端访问后端 LLM 统一通过代理，避免 CORS。

## Windows-Specific

- `New-Item -ItemType Directory` - no mkdir
- Avoid `&&` - use semicolons or run sequentially