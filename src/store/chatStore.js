import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import { MessageRole, ModelProvider } from '../types'
import { useRagStore } from './ragStore'
import { useAgentStore } from './agentStore'
import { useModelStore } from './modelStore'

const API_URL = 'http://localhost:3001'

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

const TOOL_PROMPT = `
You have access to tools. When you need to use a tool, respond in this JSON format:
{"tool": "tool_name", "args": {"param1": "value1", "param2": "value2"}}

Available tools:
${Object.entries(TOOL_DEFINITIONS).map(([name, def]) => 
  `- ${name}: ${def.description}. Params: ${Object.entries(def.parameters).map(([k, v]) => `${k}${v.required ? '*' : ''}`).join(', ')}`
).join('\n')}

After getting the result, continue with your response or call more tools.
When finished, respond with {"done": true, "response": "your answer"}
`

function parseToolCall(text) {
  try {
    const trimmed = text.trim()
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      const parsed = JSON.parse(trimmed)
      if (parsed.tool && TOOL_DEFINITIONS[parsed.tool]) {
        return parsed
      }
      if (parsed.done) {
        return { done: true, response: parsed.response }
      }
    }
  } catch (e) {}
  return null
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

  sendMessage: async (content) => {
    const { addMessage, setProcessing, executeWithRAG } = get()
    
    addMessage(MessageRole.USER, content)
    setProcessing(true)

    const ragContext = await executeWithRAG(content)
    let fullPrompt = content
    if (ragContext) fullPrompt = `User query: ${content}\n${ragContext}`

    const chatHistory = get().messages.slice(-10)
    
    try {
      const modelStore = useModelStore.getState()
      const activeModel = modelStore.getActiveModel()
      const agentStore = useAgentStore.getState()
      const mainAgent = agentStore.getMainAgent()

      const messages = [
        { role: 'system', content: TOOL_PROMPT },
        ...chatHistory.map(m => ({
          role: m.role === MessageRole.USER ? 'user' : 'assistant',
          content: m.content
        })),
        { role: 'user', content: fullPrompt }
      ]

      let maxIterations = 10
      let response = null

      while (maxIterations-- > 0) {
        const llmResponse = await callLLM(messages, activeModel, mainAgent)
        
        if (!llmResponse) {
          addMessage(MessageRole.SYSTEM, 'Failed to get response from model')
          break
        }

        const toolCall = parseToolCall(llmResponse)

        if (toolCall?.done) {
          response = toolCall.response
          addMessage(MessageRole.ASSISTANT, response, agentStore.mainAgentId, { modelId: activeModel?.id })
          break
        }

        if (toolCall?.tool) {
          messages.push({ role: 'assistant', content: llmResponse })
          const result = await executeToolBackend(toolCall.tool, toolCall.args)
          messages.push({ role: 'user', content: `Tool ${toolCall.tool} result:\n${result}` })
          continue
        }

        if (llmResponse.length < 500) {
          response = llmResponse
          addMessage(MessageRole.ASSISTANT, response, agentStore.mainAgentId, { modelId: activeModel?.id })
          break
        }

        break
      }
      
      setProcessing(false)
      return response
    } catch (error) {
      addMessage(MessageRole.SYSTEM, `Error: ${error.message}`)
      setProcessing(false)
      return null
    }
  }
}))

async function callLLM(messages, model, agent) {
  if (!model) return "No model selected. Please configure a model in Settings."
  
  const isOllama = model.provider === ModelProvider.OLLAMA
  const isOpenAI = model.provider === ModelProvider.OPENAI
  
  if (isOllama) {
    const endpoint = model.endpoint || 'http://localhost:11434'
    const modelName = model.model || 'llama2'
    
    const response = await fetch(`${endpoint}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelName, messages, stream: false })
    })
    
    if (!response.ok) throw new Error(`Ollama API error: ${response.status}`)
    const data = await response.json()
    return data.message?.content || data.response || "No response from model"
  }
  
  if (isOpenAI) {
    if (!model.apiKey) return "OpenAI API key not configured."
    
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${model.apiKey}`
      },
      body: JSON.stringify({
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