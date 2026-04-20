import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import { MessageRole, ModelProvider } from '../types'
import { useRagStore } from './ragStore'
import { useAgentStore } from './agentStore'
import { useModelStore } from './modelStore'

export const useChatStore = create((set, get) => ({
  messages: [],
  isProcessing: false,
  currentStream: '',

  addMessage: (role, content, agentId = null, metadata = {}) => {
    const message = {
      id: uuidv4(),
      role,
      content,
      agentId,
      timestamp: Date.now(),
      metadata
    }
    set((state) => ({
      messages: [...state.messages, message]
    }))
    return message
  },

  updateMessage: (messageId, updates) => set((state) => ({
    messages: state.messages.map(m =>
      m.id === messageId ? { ...m, ...updates } : m
    )
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
    
    if (context) {
      return `\n\n--- RAG Context ---\n${context}\n--- End Context ---\n\n`
    }
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

  sendMessage: async (content) => {
    const { addMessage, setProcessing, executeWithRAG } = get()
    
    addMessage(MessageRole.USER, content)
    setProcessing(true)

    const ragContext = await executeWithRAG(content)
    let fullPrompt = content
    if (ragContext) {
      fullPrompt = `User query: ${content}\n${ragContext}`
    }

    const chatHistory = get().messages.slice(-10)
    
    try {
      const modelStore = useModelStore.getState()
      const activeModel = modelStore.getActiveModel()
      
      const agentStore = useAgentStore.getState()
      const mainAgent = agentStore.getMainAgent()
      
      const response = await callLLM(fullPrompt, chatHistory, activeModel, mainAgent)
      
      addMessage(MessageRole.ASSISTANT, response, agentStore.mainAgentId, { modelId: activeModel?.id })
      
      setProcessing(false)
      return response
    } catch (error) {
      addMessage(MessageRole.SYSTEM, `Error: ${error.message}`)
      setProcessing(false)
      return null
    }
  }
}))

async function callLLM(prompt, history, model, agent) {
  if (!model) {
    return "No model selected. Please configure a model in Settings."
  }
  
  const isOllama = model.provider === ModelProvider.OLLAMA
  const isOpenAI = model.provider === ModelProvider.OPENAI
  
  if (isOllama) {
    const endpoint = model.endpoint || 'http://localhost:11434'
    const modelName = model.model || 'llama2'
    
    const messages = history.map(m => ({
      role: m.role === MessageRole.USER ? 'user' : m.role === MessageRole.ASSISTANT ? 'assistant' : 'system',
      content: m.content
    }))
    messages.push({ role: 'user', content: prompt })
    
    const response = await fetch(`${endpoint}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: modelName,
        messages: messages,
        stream: false
      })
    })
    
    if (!response.ok) {
      throw new Error(`Ollama API error: ${response.status}`)
    }
    
    const data = await response.json()
    return data.message?.content || data.response || "No response from model"
  }
  
  if (isOpenAI) {
    if (!model.apiKey) {
      return "OpenAI API key not configured. Please add your API key in Settings."
    }
    
    const messages = history.map(m => ({
      role: m.role === MessageRole.USER ? 'user' : m.role === MessageRole.ASSISTANT ? 'assistant' : 'system',
      content: m.content
    }))
    messages.push({ role: 'user', content: prompt })
    
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${model.apiKey}`
      },
      body: JSON.stringify({
        model: model.id === 'gpt-4' ? 'gpt-4' : model.id === 'gpt-4-turbo' ? 'gpt-4-turbo' : 'gpt-3.5-turbo',
        messages: messages,
        temperature: model.temperature || 0.7,
        max_tokens: model.maxTokens || 4096
      })
    })
    
    if (!response.ok) {
      throw new Error(`OpenAI API error: ${response.status}`)
    }
    
    const data = await response.json()
    return data.choices?.[0]?.message?.content || "No response from model"
  }
  
  return `Model ${model.name} is not yet supported. Please use Ollama or configure OpenAI API key.`
}