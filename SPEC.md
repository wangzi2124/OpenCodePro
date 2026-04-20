# OpenCode Pro - AI Agent Collaboration Platform

## 1. Project Overview

**Project Name**: OpenCode Pro  
**Type**: Web Application (React)  
**Core Functionality**: An AI-powered coding assistant platform with configurable models, multiple agent types (main/auxiliary), MCP (Model Communication Protocol) support, and RAG-based knowledge retrieval.  
**Target Users**: Developers who want an intelligent, collaborative coding assistant with customizable agent configurations.

---

## 2. UI/UX Specification

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ Header: Logo | Model Selector | Agent Status | Settings          │
├───────────────┬─────────────────────────────────────────────────┤
│               │                                                  │
│   Sidebar     │              Main Content Area                  │
│   - Agents    │              - Chat/Command Interface             │
│   - RAG KB    │              - Agent Response Display            │
│   - MCP       │              - Code Output                        │
│   - Settings │                                                  │
│               │                                                  │
├───────────────┴─────────────────────────────────────────────────┤
│ Footer: Status Bar | Connection Status | Agent Activity          │
└─────────────────────────────────────────────────────────────────┘
```

**Responsive Breakpoints**:
- Mobile: < 768px (stacked layout, collapsible sidebar)
- Tablet: 768px - 1024px (compact sidebar)
- Desktop: > 1024px (full layout)

### Visual Design

**Color Palette**:
- Background Primary: `#0D1117` (dark navy)
- Background Secondary: `#161B22` (lighter navy)
- Background Tertiary: `#21262D` (card backgrounds)
- Accent Primary: `#58A6FF` (blue - main actions)
- Accent Secondary: `#7EE787` (green - success/active)
- Accent Warning: `#D29922` (amber - warnings)
- Accent Error: `#F85149` (red - errors)
- Text Primary: `#E6EDF3` (white)
- Text Secondary: `#8B949E` (gray)
- Border: `#30363D` (dark gray)

**Typography**:
- Font Family: `"JetBrains Mono", "Fira Code", monospace` (code/terminal)
- Font Family UI: `"Inter", -apple-system, sans-serif` (UI elements)
- Headings: 24px (h1), 20px (h2), 16px (h3)
- Body: 14px
- Code: 13px

**Spacing**:
- Base unit: 4px
- Margins: 16px, 24px, 32px
- Padding: 8px, 12px, 16px

**Visual Effects**:
- Card shadows: `0 4px 12px rgba(0, 0, 0, 0.4)`
- Hover transitions: 150ms ease
- Active agent glow: `box-shadow: 0 0 12px #7EE787`
- Terminal-style scanlines (subtle)

### Components

1. **Header**
   - Logo with animated gradient
   - Model dropdown selector (configurable)
   - Agent status indicator (colored dot)
   - Settings gear icon

2. **Sidebar**
   - Collapsible sections
   - Agent list with status (online/offline/busy)
   - RAG Knowledge Base browser
   - MCP server list
   - Quick settings access

3. **Main Chat Area**
   - Message bubbles (user vs agent)
   - Code blocks with syntax highlighting
   - Markdown support
   - Agent attribution tags

4. **Agent Configuration Panel**
   - Model selection
   - Temperature/top-p sliders
   - System prompt editor
   - Tool permissions

5. **RAG Panel**
   - Document upload
   - Search interface
   - Knowledge chunks display

6. **Terminal Output**
   - Monospace font
   - ANSI color support
   - Auto-scroll
   - Copy button

---

## 3. Functionality Specification

### Core Features

#### 3.1 Model Configuration
- Manual model selection (dropdown)
- Supported models: GPT-4, Claude, Gemini, Local models (Ollama)
- Model parameters: temperature, top_p, max_tokens
- API key management (secure storage)

#### 3.2 Agent System

**Main Agent**:
- Central coordinator
- Task decomposition
- Delegates to auxiliary agents
- Integrates results
- Maintains conversation context

**Auxiliary Agents**:
- File Agent: File operations (read, write, search)
- Code Agent: Code analysis and generation
- Bash Agent: Command execution
- Web Agent: Web searches and fetching
- Research Agent: RAG-based knowledge lookup
- Custom Agents: User-defined specialized agents

**Agent Lifecycle**:
- Agent spawn (create new agent instance)
- Agent task (assign task to agent)
- Agent response (receive agent output)
- Agent kill (terminate agent)
- Agent status: idle, working, completed, failed

#### 3.3 MCP (Model Communication Protocol)
- Define agent communication protocols
- Message format: `{ from, to, action, payload }`
- Protocol templates
- Event-driven messaging

#### 3.4 RAG (Retrieval-Augmented Generation)
- Document ingestion (PDF, MD, TXT, Code)
- Chunking strategies
- Vector embedding
- Semantic search
- Context injection
- Knowledge base management

#### 3.5 Subagent Management
- Create subagents from main agent
- Task assignment
- Result aggregation
- Agent tree visualization

#### 3.6 Agent Kill
- Graceful termination
- Force kill option
- Cleanup resources
- Status update

### User Interactions

1. **Send Message** → Main Agent receives
2. **Model Select** → Updates active model
3. **Spawn Agent** → Creates new auxiliary agent
4. **Kill Agent** → Terminates selected agent
5. **Upload Document** → Adds to RAG knowledge base
6. **Search Knowledge** → RAG semantic search
7. **Configure Agent** → Opens config panel

### Edge Cases
- Agent timeout handling
- API rate limiting
- Network disconnection
- RAG index corruption
- Concurrent agent limits
- Resource exhaustion

---

## 4. Acceptance Criteria

1. ✅ Model selector allows manual configuration
2. ✅ Main agent coordinates auxiliary agents
3. ✅ Can create/spawn different agent types
4. ✅ Agents can communicate via MCP
5. ✅ Subagent results aggregated by main agent
6. ✅ Agent kill terminates without hanging
7. ✅ RAG search returns relevant context
8. ✅ Real-time agent status display
9. ✅ Responsive on all screen sizes
10. ✅ Terminal-style output with ANSI colors