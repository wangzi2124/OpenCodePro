import { create } from 'zustand'
import { ModelProvider } from '../types'

const defaultModels = [
  { id: 'llama3:latest', name: 'llama3 (Local)', provider: ModelProvider.CUSTOM, endpoint: 'http://localhost:11434', apiKey: '', temperature: 0.7, topP: 0.9, maxTokens: 512, isLocal: true },
  { id: 'mistral:latest', name: 'mistral (Local)', provider: ModelProvider.CUSTOM, endpoint: 'http://localhost:11434', apiKey: '', temperature: 0.7, topP: 0.9, maxTokens: 4096, isLocal: true },
  { id: 'qwen2.5-coder:latest', name: 'qwen2.5-coder (Local)', provider: ModelProvider.CUSTOM, endpoint: 'http://localhost:11434', apiKey: '', temperature: 0.7, topP: 0.9, maxTokens: 4096, isLocal: true },

]

export const useModelStore = create((set, get) => ({
  models: defaultModels,
  customModels: [],
  activeModelId: 'llama3:latest',

  setActiveModel: (modelId) => set({ activeModelId: modelId }),

  addModel: (model) => set((state) => ({
    customModels: [...state.customModels, { ...model, id: `custom-${Date.now()}` }]
  })),

  updateModel: (modelId, updates) => set((state) => ({
    models: state.models.map(m => m.id === modelId ? { ...m, ...updates } : m),
    customModels: state.customModels.map(m => m.id === modelId ? { ...m, ...updates } : m)
  })),

  removeModel: (modelId) => set((state) => ({
    models: state.models.filter(m => m.id !== modelId),
    customModels: state.customModels.filter(m => m.id !== modelId)
  })),

  getActiveModel: () => {
    const { models, customModels, activeModelId } = get()
    return [...models, ...customModels].find(m => m.id === activeModelId)
  },

  getAllModels: () => {
    const { models, customModels } = get()
    return [...models, ...customModels]
  }
}))
