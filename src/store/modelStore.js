import { create } from 'zustand'
import { ModelProvider } from '../types'

const defaultModels = [
  { id: 'qwen2.5:latest', name: 'Qwen 2.5 (Local)', provider: ModelProvider.CUSTOM, endpoint: 'http://localhost:11434', apiKey: '', temperature: 0.7, topP: 0.9, maxTokens: 512, isLocal: true },
  { id: 'llama2:latest', name: 'Llama 2 (Local)', provider: ModelProvider.CUSTOM, endpoint: 'http://localhost:11434', apiKey: '', temperature: 0.7, topP: 0.9, maxTokens: 4096, isLocal: true },
]

export const useModelStore = create((set, get) => ({
  models: defaultModels,
  activeModelId: 'qwen2.5:latest',

  setActiveModel: (modelId) => set({ activeModelId: modelId }),

  updateModel: (modelId, updates) => set((state) => ({
    models: state.models.map(m => m.id === modelId ? { ...m, ...updates } : m)
  })),

  getActiveModel: () => {
    const { models, activeModelId } = get()
    return models.find(m => m.id === activeModelId)
  },

  getAllModels: () => {
    const { models } = get()
    return models
  }
}))
