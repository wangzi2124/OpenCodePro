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
├── store/        # Zustand stores (modelStore, agentStore, ragStore, chatStore)
├── types/        # Enums (AgentType, AgentStatus, ModelProvider, MCPAction, MessageRole)
├── styles/       # Global CSS
├── App.jsx       # Main entry
└── main.jsx      # React entry
```

## Agent System

Main Agent coordinates: FILE, CODE, BASH, WEB, RESEARCH agents via MCP protocol (SPAWN, TASK, RESPONSE, KILL, STATUS).

## Windows-Specific

- `New-Item -ItemType Directory` - no mkdir
- Avoid `&&` - use semicolons or separate commands