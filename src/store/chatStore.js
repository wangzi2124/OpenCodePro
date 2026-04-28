import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import { MessageRole, ModelProvider } from '../types'
import { useRagStore } from './ragStore'
import { useAgentStore } from './agentStore'
import { useModelStore } from './modelStore'

const API_URL = 'http://localhost:3001'

const REACT_SYSTEM_PROMPT = `You are an expert AI assistant that combines deep reasoning with powerful tools to solve complex tasks efficiently.

You operate using the ReAct (Reasoning + Acting) pattern with structured output tags:

<thought>Your reasoning process - analyze the problem, plan your approach, evaluate what tools are needed</thought>
<action>tool_name:arg1:value1,arg2:value2</action>
<observation>Tool execution result will appear here</observation>
<final_answer>Your comprehensive answer to the user</final_answer>

Example interaction:
User: Read the package.json and tell me the project name

<thought>The user wants me to read a file and extract information. I should use the read tool to access package.json first.</thought>
<action>read:filePath:/path/to/package.json</action>
<observation>{"name": "my-project", "version": "1.0.0", "description": "A sample project"}</observation>
<thought>I received the file content. The project name is "my-project" and version is "1.0.0".</thought>
<final_answer>The project name is "my-project" (version 1.0.0).</final_answer>

Core Rules:
1. Always start with <thought> to show your reasoning
2. Use <action> when you need to access external information or perform operations
3. Results appear in <observation> - use them to refine your thinking
4. End with <final_answer> when you have a complete solution
5. Bash commands require user confirmation before execution
6. Chain multiple tools when needed for complex tasks

Available Tools:
- read:filePath:<path> - Read file contents (supports large files with offset/limit)
- write:filePath:<path>,content:<content> - Create or overwrite a file
- edit:filePath:<path>,oldString:<text>,newString:<text> - Modify existing files
- glob:pattern:<glob> - Find files by pattern (e.g., **/*.js, src/**/*.{ts,tsx})
- grep:pattern:<regex>,include:<file_pattern>,path:<directory> - Search file contents
- bash:command:<cmd> - Execute terminal commands
- web:url:<url> - Fetch web page content
- search:query:<query> - Search the web for information
- code:query:<question> - Search programming examples/documentation`

const TOOL_DEFINITIONS = {
  read: {
    name: 'read',
    description: 'Read a file and return its content',
    parameters: {
      filePath: { type: 'string', required: true, description: 'Absolute path to the file' }
    }
  },
  write: {
    name: 'write',
    description: 'Write content to a file (creates or overwrites)',
    parameters: {
      filePath: { type: 'string', required: true, description: 'Absolute path to the file' },
      content: { type: 'string', required: true, description: 'Content to write' }
    }
  },
  edit: {
    name: 'edit',
    description: 'Edit a file by replacing specific text',
    parameters: {
      filePath: { type: 'string', required: true, description: 'Absolute path to the file' },
      oldString: { type: 'string', required: true, description: 'Text to find' },
      newString: { type: 'string', required: true, description: 'Text to replace with' }
    }
  },
  glob: {
    name: 'glob',
    description: 'Find files matching a pattern',
    parameters: {
      pattern: { type: 'string', required: true, description: 'Glob pattern (e.g., **/*.js)' }
    }
  },
  grep: {
    name: 'grep',
    description: 'Search for text in files',
    parameters: {
      pattern: { type: 'string', required: true, description: 'Regex pattern to search' },
      include: { type: 'string', required: false, description: 'File pattern (e.g., *.js)' }
    }
  },
  bash: {
    name: 'bash',
    description: 'Execute a bash command',
    parameters: {
      command: { type: 'string', required: true, description: 'Command to execute' }
    }
  },
  web: {
    name: 'web',
    description: 'Fetch a URL and get its content',
    parameters: {
      url: { type: 'string', required: true, description: 'URL to fetch' }
    }
  },
  search: {
    name: 'search',
    description: 'Web search for information',
    parameters: {
      query: { type: 'string', required: true, description: 'Search query' }
    }
  },
  code: {
    name: 'code',
    description: 'Search for programming code examples and patterns from GitHub',
    parameters: {
      query: { type: 'string', required: true, description: 'Code search query (e.g., "useState React hooks")' },
      language: { type: 'string', required: false, description: 'Programming language filter (e.g., TypeScript, Python)' }
    }
  }
}

function parseReActTags(text) {
  let thought = null, action = null, finalAnswer = null, observation = null
  
  const thoughtMatch = text.match(/<thought>([\s\S]*?)<\/thought>/)
  const actionMatch = text.match(/<action>([\s\S]*?)<\/action>/)
  const finalAnswerMatch = text.match(/<final_answer>([\s\S]*?)<\/final_answer>/)
  const observationMatch = text.match(/<observation>([\s\S]*?)<\/observation>/)
  
  thought = thoughtMatch ? thoughtMatch[1].trim() : null
  observation = observationMatch ? observationMatch[1].trim() : null
  
  if (finalAnswerMatch) {
    finalAnswer = finalAnswerMatch[1].trim()
  } else if (actionMatch) {
    action = actionMatch[1].trim()
  } else {
    const jsonResult = parseJsonOutput(text)
    if (jsonResult) {
      finalAnswer = jsonResult.finalAnswer
      action = jsonResult.action
    } else {
      finalAnswer = text.trim()
    }
  }
  
  return { thought, action, finalAnswer, observation }
}

function parseJsonOutput(text) {
  try {
    const json = JSON.parse(text.trim())
    
    const finalKey = Object.keys(json).find(k => k.toLowerCase() === 'final_answer' || k.toLowerCase() === 'answer')
    if (finalKey !== undefined) {
      return { finalAnswer: json[finalKey] }
    }
    
    const toolKey = Object.keys(json).find(k => 
      k.toLowerCase() === 'tool' || 
      k.toLowerCase().includes('read') || k.toLowerCase().includes('write') ||
      k.toLowerCase().includes('edit') || k.toLowerCase().includes('glob') ||
      k.toLowerCase().includes('grep') || k.toLowerCase().includes('bash') ||
      k.toLowerCase().includes('run') || k.toLowerCase().includes('fetch') ||
      k.toLowerCase().includes('search') || k.toLowerCase().includes('code')
    )
    if (toolKey) {
      const toolName = json[toolKey]
      if (TOOL_DEFINITIONS[toolName]) {
        const args = json.args || {}
        return { action: JSON.stringify({ tool: toolName, args }) }
      }
    }
  } catch {}
  return null
}

function parseAction(actionStr) {
  if (!actionStr) return null
  
  const jsonClean = actionStr.replace(/^\s*/, '').replace(/\s*$/, '').trim()
  
  try {
    const json = JSON.parse(jsonClean)
    
    const finalKey = Object.keys(json).find(k => k.toLowerCase() === 'final_answer' || k.toLowerCase() === 'answer')
    if (finalKey) {
      return { finalAnswer: json[finalKey] }
    }
    
    const toolKey = Object.keys(json).find(k => 
      k.toLowerCase() === 'tool' || k.toLowerCase().includes('read') || 
      k.toLowerCase().includes('write') || k.toLowerCase().includes('edit') ||
      k.toLowerCase().includes('glob') || k.toLowerCase().includes('grep') ||
      k.toLowerCase().includes('bash') || k.toLowerCase().includes('run') ||
      k.toLowerCase().includes('fetch') || k.toLowerCase().includes('search')
    )
    if (toolKey) {
      const toolMap = {
        read_file: 'read', file_read: 'read', Read: 'read', 'read file': 'read',
        write_file: 'write', file_write: 'write', Write: 'write', 'write file': 'write',
        edit_file: 'edit', file_edit: 'edit', Edit: 'edit', 'edit file': 'edit',
        glob_file: 'glob', file_glob: 'glob', Glob: 'glob', 'glob file': 'glob',
        grep_search: 'grep', Grep: 'grep',
        run_bash: 'bash', bash_run: 'bash', Run: 'bash', bash: 'bash', command: 'bash',
        web_fetch: 'fetch', fetch_url: 'fetch', Fetch: 'fetch',
        web_search: 'search', Search: 'search',
        code_search: 'code', Code: 'code', 'code search': 'code'
      }
      
      const toolName = toolMap[json[toolKey]] || json[toolKey]
      
      if (TOOL_DEFINITIONS[toolName]) {
        let args = {}
        if (json.args && typeof json.args === 'object') {
          args = json.args
        } else {
          for (const [k, v] of Object.entries(json)) {
            if (k !== toolKey) args[k] = v
          }
        }
        return { tool: toolName, args }
      }
    }
  } catch {}
  
  let toolName, argsStr
  let match = actionStr.match(/^(\w+)-(\w+):(.+)$/)
  if (match) {
    toolName = match[2]
    argsStr = match[3]
  } else {
    match = actionStr.match(/^(\w+)_(\w+):(.+)$/)
    if (match) {
      toolName = match[2]
      argsStr = match[3]
    } else {
      match = actionStr.match(/^(\w+):(.+)$/)
      if (!match) return null
      toolName = match[1]
      argsStr = match[2]
    }
  }

  if ((toolName === 'write' || toolName === 'file') && argsStr.includes(':') && argsStr.includes(',')) {
    const firstCommaIndex = argsStr.indexOf(',');
    const filePath = argsStr.substring(0, firstCommaIndex);
    const content = argsStr.substring(firstCommaIndex + 1);
    const contentValue = content.replace(/^content:/, '');
    if (filePath && contentValue) {
      const finalTool = toolName === 'file' ? 'write' : toolName
      return { tool: finalTool, args: { filePath, content: contentValue } }
    }
  }

  if ((toolName === 'write' || toolName === 'file') && argsStr.includes(':') && !argsStr.startsWith('filePath:')) {
    const lastColon = argsStr.lastIndexOf(':');
    const filePath = argsStr.substring(0, lastColon);
    const content = argsStr.substring(lastColon + 1);
    if (filePath && content) {
      const finalTool = toolName === 'file' ? 'write' : toolName
      return { tool: finalTool, args: { filePath, content } }
    }
  }

  const args = {}
  const argMatches = argsStr.matchAll(/(\w+):([^,]+)/g)
  for (const m of argMatches) {
    args[m[1]] = m[2].trim()
  }

  if (TOOL_DEFINITIONS[toolName]) {
    return { tool: toolName, args }
  }
  return null
}

function extractThoughts(text) {
  const thoughts = []
  const regex = /<thought>([\s\S]*?)<\/thought>/g
  let match
  while ((match = regex.exec(text)) !== null) {
    thoughts.push(match[1].trim())
  }
  return thoughts
}

async function executeToolBackend(toolName, args) {
  const mapToolName = { web: 'fetch' }
  const apiTool = mapToolName[toolName] || toolName

  const finalArgs = args || {}
  
  for (const [k, v] of Object.entries(args || {})) {
    if (k !== 'tool' && k !== 'args' && typeof v === 'object') {
      Object.assign(finalArgs, v)
    }
  }

  try {
    const res = await fetch(`${API_URL}/api/tool`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool: apiTool, args: finalArgs })
    })
    const result = await res.json()

    if (result.error) return `Error: ${result.error}`
    if (result.content) return result.content
    if (result.message) return result.message
    if (result.stdout) return result.stdout
    if (result.files) return result.files.join('\n')
    if (result.results) return result.results
    if (result.success) return JSON.stringify(result)
    return JSON.stringify(result)
  } catch (e) {
    return `Tool error: ${e.message}`
  }
}

export const useChatStore = create((set, get) => ({
  messages: [],
  isProcessing: false,
  currentStream: '',

  addMessage: (role, content, agentId = null, metadata = {}) => {
    const message = { id: uuidv4(), role, content, agentId, timestamp: Date.now(), metadata }
    set((state) => ({ messages: [...state.messages, message] }))
    return message
  },

  updateMessage: (messageId, updates) => set((state) => ({
    messages: state.messages.map(m => m.id === messageId ? { ...m, ...updates } : m)
  })),

  deleteMessage: (messageId) => set((state) => ({
    messages: state.messages.filter(m => m.id !== messageId)
  })),

  clearMessages: () => set({ messages: [], currentStream: '' }),
  setProcessing: (isProcessing) => set({ isProcessing }),
  setStream: (content) => set({ currentStream: content }),

  streamResponse: async (content) => {
    set((state) => ({ currentStream: state.currentStream + content }))
  },

  finishStream: () => {
    const { currentStream, addMessage } = get()
    if (currentStream) {
      addMessage(MessageRole.ASSISTANT, currentStream)
      set({ currentStream: '' })
    }
  },

  executeWithRAG: async (query) => {
    const ragStore = useRagStore.getState()
    const context = await ragStore.getContext(query, 2000)
    if (context) return `\n\n--- RAG Context ---\n${context}\n--- End Context ---\n\n`
    return ''
  },

  routeToAgent: async (task, agentType) => {
    const agentStore = useAgentStore.getState()
    const agentId = agentStore.spawnAgent(agentType, { parentId: agentStore.mainAgentId })
    if (agentId) {
      agentStore.assignTask(agentId, task)
      return agentId
    }
    return null
  },

  async executeTool(toolName, args) {
    return executeToolBackend(toolName, args)
  },

  pendingBashCommand: null,

  setPendingBashCommand: (cmd) => set({ pendingBashCommand: cmd }),

  confirmBashCommand: async () => {
    const { pendingBashCommand, messages, addMessage, setProcessing } = get()
    if (!pendingBashCommand) return

    set({ pendingBashCommand: null })
    setProcessing(true)

    const modelStore = useModelStore.getState()
    const activeModel = modelStore.getActiveModel()
    const agentStore = useAgentStore.getState()
    const mainAgent = agentStore.getMainAgent()

    const chatHistory = messages.filter(m => m.role !== MessageRole.SYSTEM)

    const llmMessages = [
      { role: 'system', content: REACT_SYSTEM_PROMPT },
      ...chatHistory.map(m => ({
        role: m.role === MessageRole.USER ? 'user' : 'assistant',
        content: m.content
      })),
      { role: 'user', content: `<observation>User confirmed command: ${pendingBashCommand.command}\nExecuting...</observation>` }
    ]

    const result = await executeToolBackend('bash', { command: pendingBashCommand.command })
    llmMessages.push({ role: 'user', content: `<observation>${result}</observation>` })

    await runReActLoop(llmMessages, activeModel, mainAgent, agentStore.mainAgentId)
  },

  rejectBashCommand: () => {
    set({ pendingBashCommand: null })
    addMessage(MessageRole.SYSTEM, 'Command rejected by user')
  },

  sendMessage: async (content) => {
    const { addMessage, setProcessing, executeWithRAG } = get()
    
    addMessage(MessageRole.USER, content)
    setProcessing(true)

    const ragContext = await executeWithRAG(content)
    let fullPrompt = content
    if (ragContext) fullPrompt = `User query: ${content}\n${ragContext}`

    const chatHistory = get().messages.filter(m => m.role !== MessageRole.SYSTEM).slice(-10)
    
    try {
      const modelStore = useModelStore.getState()
      const activeModel = modelStore.getActiveModel()
      const agentStore = useAgentStore.getState()
      const mainAgent = agentStore.getMainAgent()

      const messages = [
        { role: 'system', content: REACT_SYSTEM_PROMPT },
        ...chatHistory.map(m => ({
          role: m.role === MessageRole.USER ? 'user' : 'assistant',
          content: m.content
        })),
        { role: 'user', content: fullPrompt }
      ]

      await runReActLoop(messages, activeModel, mainAgent, agentStore.mainAgentId)
    } catch (error) {
      addMessage(MessageRole.SYSTEM, `Error: ${error.message}`)
      setProcessing(false)
    }
  }
}))

async function runReActLoop(messages, activeModel, mainAgent, agentId) {
  const chatStore = useChatStore.getState()
  const { addMessage, setProcessing, updateMessage, setPendingBashCommand } = chatStore

  let currentMessageId = null
  let maxIterations = 15

  while (maxIterations-- > 0) {
    const llmResponse = await callLLM(messages, activeModel, mainAgent)
    
    if (!llmResponse) {
      addMessage(MessageRole.SYSTEM, 'Failed to get response from model')
      break
    }

    const { thought, action, finalAnswer, observation } = parseReActTags(llmResponse)

    if (thought) {
      const fullThoughts = extractThoughts(messages.map(m => m.content).join('\n'))
      let thoughtText = fullThoughts.map(t => `• ${t}`).join('\n\n')
      if (thought) {
        thoughtText += (thoughtText ? '\n\n' : '') + `• ${thought}`
      }

      if (currentMessageId) {
        updateMessage(currentMessageId, { content: `**Thinking:**\n\n${thoughtText}` })
      } else {
        const msg = addMessage(MessageRole.ASSISTANT, `**Thinking:**\n\n${thoughtText}`, agentId, { modelId: activeModel?.id, isThinking: true })
        currentMessageId = msg.id
      }
    }

    if (finalAnswer) {
      if (currentMessageId) {
        updateMessage(currentMessageId, { content: finalAnswer, metadata: { ...chatStore.messages.find(m => m.id === currentMessageId)?.metadata, isThinking: false } })
      } else {
        addMessage(MessageRole.ASSISTANT, finalAnswer, agentId, { modelId: activeModel?.id })
      }
      break
    }

    if (action) {
      const toolCall = parseAction(action)
      if (!toolCall) continue

      if (toolCall.tool === 'bash') {
        const cmd = toolCall.args.command
        addMessage(MessageRole.SYSTEM, `⚠️ Confirm to execute this command?\n\`\`\`\n${cmd}\n\`\`\``)
        setPendingBashCommand({ command: cmd })
        return
      }

      messages.push({ role: 'assistant', content: llmResponse })
      
      const result = await executeToolBackend(toolCall.tool, toolCall.args)
      messages.push({ role: 'user', content: `<observation>${result}</observation>` })
      
      if (currentMessageId) {
        const currentMsg = chatStore.messages.find(m => m.id === currentMessageId)
        updateMessage(currentMessageId, { 
          content: (currentMsg?.content || '') + `\n\n**Action:** ${action}\n\n**Result:**\n\`\`\`\n${result.slice(0, 1000)}${result.length > 1000 ? '...' : ''}\n\`\`\`` 
        })
      }

      continue
    }

    if (!thought && !action && !finalAnswer) {
      if (currentMessageId) {
        updateMessage(currentMessageId, { content: llmResponse, metadata: { ...chatStore.messages.find(m => m.id === currentMessageId)?.metadata, isThinking: false } })
      } else {
        addMessage(MessageRole.ASSISTANT, llmResponse, agentId, { modelId: activeModel?.id })
      }
      break
    }
  }

  setProcessing(false)
}

async function callLLM(messages, model, agent) {
  if (!model) return "No model selected. Please configure a model in Settings."
  
  const isOllama = model.provider === ModelProvider.OLLAMA
  const isOpenAI = model.provider === ModelProvider.OPENAI
  
  if (isOllama) {
    const response = await fetch('/api/proxy/ollama', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        model: model.model || 'llama2', 
        messages, 
        stream: false 
      })
    })
    
    if (!response.ok) throw new Error(`Ollama API error: ${response.status}`)
    const data = await response.json()
    return data.message?.content || data.response || "No response from model"
  }
  
if (isOpenAI) {
  if (!model.apiKey) return "OpenAI API key not configured."
  
  const response = await fetch('/api/proxy/openai', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      apiKey: model.apiKey,
      model: model.id === 'gpt-4' ? 'gpt-4' : 'gpt-3.5-turbo',
      messages,
      temperature: model.temperature || 0.7,
      max_tokens: model.maxTokens || 4096
    })
  })
    
    if (!response.ok) throw new Error(`OpenAI API error: ${response.status}`)
    const data = await response.json()
    return data.choices?.[0]?.message?.content || "No response from model"
  }
  
  return `Model ${model.name} not supported.`
}