import { useState } from 'react'
import { useModelStore } from '../store'
import { ModelProvider } from '../types'
import './ModelModal.css'

function ModelModal() {
  const [isOpen, setIsOpen] = useState(false)
  const [editingModel, setEditingModel] = useState(null)
  
  const models = useModelStore(state => state.models)
  const customModels = useModelStore(state => state.customModels)
  const activeModelId = useModelStore(state => state.activeModelId)
  const setActiveModel = useModelStore(state => state.setActiveModel)
  const addModel = useModelStore(state => state.addModel)
  const updateModel = useModelStore(state => state.updateModel)
  const removeModel = useModelStore(state => state.removeModel)

  const allModels = [...models, ...customModels]

  const handleAddModel = () => {
    const newModel = {
      name: 'New Model',
      provider: ModelProvider.CUSTOM,
      apiKey: '',
      temperature: 0.7,
      topP: 0.9,
      maxTokens: 4096
    }
    addModel(newModel)
  }

  const handleUpdateModel = (modelId, field, value) => {
    updateModel(modelId, { [field]: value })
  }

  const handleRemoveModel = (modelId) => {
    if (modelId !== activeModelId) {
      removeModel(modelId)
    }
  }

  return (
    <>
      <button className="modal-trigger" onClick={() => setIsOpen(true)}>
        Open Model Settings
      </button>
      
      {isOpen && (
        <div className="modal-overlay" onClick={() => setIsOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Model Configuration</h2>
              <button className="close-btn" onClick={() => setIsOpen(false)}>×</button>
            </div>
            
            <div className="model-list">
              {allModels.map(model => (
                <div 
                  key={model.id} 
                  className={`model-card ${model.id === activeModelId ? 'active' : ''}`}
                >
                  <div className="model-header">
                    <input
                      type="text"
                      value={model.name}
                      onChange={(e) => handleUpdateModel(model.id, 'name', e.target.value)}
                      className="model-name-input"
                    />
                    <span className="provider-badge">{model.provider}</span>
                  </div>
                  
                  <div className="model-params">
                    <div className="param">
                      <label>Temperature</label>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={model.temperature || 0.7}
                        onChange={(e) => handleUpdateModel(model.id, 'temperature', parseFloat(e.target.value))}
                      />
                      <span>{model.temperature}</span>
                    </div>
                    
                    <div className="param">
                      <label>Top-P</label>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={model.topP || 0.9}
                        onChange={(e) => handleUpdateModel(model.id, 'topP', parseFloat(e.target.value))}
                      />
                      <span>{model.topP}</span>
                    </div>
                    
                    <div className="param">
                      <label>Max Tokens</label>
                      <input
                        type="number"
                        value={model.maxTokens || 4096}
                        onChange={(e) => handleUpdateModel(model.id, 'maxTokens', parseInt(e.target.value))}
                      />
                    </div>
                  </div>
                  
                  {model.provider === ModelProvider.CUSTOM && (
                    <div className="model-fields">
                      <input
                        type="text"
                        value={model.endpoint || ''}
                        onChange={(e) => handleUpdateModel(model.id, 'endpoint', e.target.value)}
                        placeholder="API Endpoint"
                        className="model-field"
                      />
                      <input
                        type="password"
                        value={model.apiKey || ''}
                        onChange={(e) => handleUpdateModel(model.id, 'apiKey', e.target.value)}
                        placeholder="API Key"
                        className="model-field"
                      />
                    </div>
                  )}
                  
                  <div className="model-actions">
                    <button
                      className="select-btn"
                      onClick={() => setActiveModel(model.id)}
                    >
                      {model.id === activeModelId ? '✓ Active' : 'Select'}
                    </button>
                    {model.provider === ModelProvider.CUSTOM && (
                      <button
                        className="remove-btn"
                        onClick={() => handleRemoveModel(model.id)}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            
            <button className="add-model-btn" onClick={handleAddModel}>
              + Add Custom Model
            </button>
          </div>
        </div>
      )}
    </>
  )
}

export default ModelModal