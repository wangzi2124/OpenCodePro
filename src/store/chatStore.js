import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import { MessageRole } from '../types'
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
      
      const response = await mockLLMResponse(fullPrompt, chatHistory, activeModel, mainAgent)
      
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

async function mockLLMResponse(prompt, history, model, agent) {
  await new Promise(resolve => setTimeout(resolve, 500))
  
  const responseTemplates = [
    "I've analyzed your request and can help with that. Let me break this down into tasks for my auxiliary agents.",
    "I understand you need assistance with this. I'll coordinate with specialized agents to complete your request efficiently.",
    "Your request has been received. I'm dispatching task-specific agents to help you.",
    "I'll help you with this. Based on the complexity, I'll use multiple specialized agents."
  ]
  
  const randomIndex = Math.floor(Math.random() * responseTemplates.length)
  return responseTemplates[randomIndex] + "\n\n" + `[Using model: ${model?.name || 'default'}]\n[Main Agent: ${agent?.name || 'Agent'}]`
}