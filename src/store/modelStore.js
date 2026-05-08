import { create } from 'zustand'
import { ModelProvider } from '../types'

const defaultModels = [
  { id: 'qwen2.5:latest', name: 'Qwen 2.5 (Local)', provider: ModelProvider.CUSTOM, endpoint: 'http://localhost:11434', apiKey: '', temperature: 0.7, topP: 0.9, maxTokens: 512, isLocal: true },
  { id: 'llama2:latest', name: 'Llama 2 (Local)', provider: ModelProvider.CUSTOM, endpoint: 'http://localhost:11434', apiKey: '', temperature: 0.7, topP: 0.9, maxTokens: 4096, isLocal: true },
  // Add custom API keys from settings panel
]

export const useModelStore = create((set, get) => ({
  models: defaultModels,
  activeModelId: 'qwen2.5:latest',
  customModels: [],
  translationModelId: 'qwen2.5:latest',

  setActiveModel: (modelId) => set({ activeModelId: modelId }),

  setTranslationModel: (modelId) => set({ translationModelId: modelId }),

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
