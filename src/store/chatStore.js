import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import { MessageRole, ModelProvider } from '../types'
import { useRagStore } from './ragStore'
import { useAgentStore } from './agentStore'
import { useModelStore } from './modelStore'

const API_URL = 'http://localhost:3001'

const REACT_SYSTEM_PROMPT = `You are a reasoning agent that uses the ReAct (Reasoning + Acting) format.

Output your response using these tags:
- <thought>Your reasoning about what to do</thought>
- <action>tool_name:arg1:value1,arg2:value2</action> - use this to call a tool
- <observation>tool result will be inserted here</observation>
- <final_answer>Your final answer to the user</final_answer>

Example:
<thought>I need to read the file to understand its structure</thought>
<action>read:filePath:/path/to/file.txt</action>
<observation>File content here...</observation>
<thought>Now I understand the file structure</thought>
<final_answer>The file contains...</final_answer>

Rules:
1. Always start with <thought>
2. Use <action> to call tools when needed
3. After each action, you will receive the result in <observation>
4. When you have the answer, use <final_answer>
5. For bash commands, wait for user confirmation before executing
6. Other tools will be executed automatically

Available tools:
- read:filePath:<path> - Read a file
- write:filePath:<path>,content:<content> - Write to a file
- edit:filePath:<path>,oldString:<text>,newString:<text> - Edit a file
- glob:pattern:<glob> - Find files by pattern
- grep:pattern:<regex>,include:<file_pattern> - Search in files
- bash:command:<cmd> - Execute bash command (requires confirmation)
- web:url:<url> - Fetch URL content
- search:query:<query> - Web search`

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
  }
}

function parseReActTags(text) {
  const thoughtMatch = text.match(/<thought>([\s\S]*?)<\/thought>/)
  const actionMatch = text.match(/<action>([\s\S]*?)<\/action>/)
  const finalAnswerMatch = text.match(/<final_answer>([\s\S]*?)<\/final_answer>/)
  const observationMatch = text.match(/<observation>([\s\S]*?)<\/observation>/)

  return {
    thought: thoughtMatch ? thoughtMatch[1].trim() : null,
    action: actionMatch ? actionMatch[1].trim() : null,
    finalAnswer: finalAnswerMatch ? finalAnswerMatch[1].trim() : null,
    observation: observationMatch ? observationMatch[1].trim() : null
  }
}

function parseAction(actionStr) {
  if (!actionStr) return null
  
  const match = actionStr.match(/^(\w+):(.+)$/)
  if (!match) return null

  const toolName = match[1]
  const argsStr = match[2]
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

  try {
    const res = await fetch(`${API_URL}/api/tool`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tool: apiTool, args })
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
      
      if (!toolCall) {
        addMessage(MessageRole.SYSTEM, `Invalid action format: ${action}`)
        break
      }

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