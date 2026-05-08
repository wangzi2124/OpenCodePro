import { useState, useEffect } from 'react'
import { useModelStore } from '../store'
import { ModelProvider } from '../types'
import './Sidebar.css'

function Sidebar() {
  const [activeTab, setActiveTab] = useState('settings')

  const models = useModelStore(state => state.models)
  const customModels = useModelStore(state => state.customModels)
  const activeModelId = useModelStore(state => state.activeModelId)
  const setActiveModel = useModelStore(state => state.setActiveModel)
  const addModel = useModelStore(state => state.addModel)
  const updateModel = useModelStore(state => state.updateModel)
  const removeModel = useModelStore(state => state.removeModel)
  const getActiveModel = useModelStore(state => state.getActiveModel)

  const [activeModelData, setActiveModelData] = useState(null)

  useEffect(() => {
    setActiveModelData(getActiveModel())
  }, [activeModelId, getActiveModel])

  const allModels = [...models, ...customModels]

  const handleAddModel = () => {
    addModel({
      name: 'New Model',
      provider: ModelProvider.CUSTOM,
      apiKey: '',
      endpoint: '',
      temperature: 0.7,
      maxTokens: 4096
    })
  }

  const tabs = [
    { id: 'models', label: 'Models', icon: '🤖' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`sidebar-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
            title={tab.label}
          >
            <span className="tab-icon">{tab.icon}</span>
          </button>
        ))}
      </div>

      <div className="sidebar-content">
        {activeTab === 'models' && (
          <div className="agents-panel">
            <div className="panel-header">
              <h3>ReAct Agent</h3>
            </div>
            <div className="agent-status-card">
              <div className="status-row">
                <span>状态</span>
                <span className="status-badge idle">就绪</span>
              </div>
              <div className="status-row">
                <span>模型</span>
                <span className="status-value">{activeModelData?.name || '未选择'}</span>
              </div>
              <div className="status-row">
                <span>工具</span>
                <span className="status-value">9 内置工具</span>
              </div>
              <div className="status-row">
                <span>模式</span>
                <span className="status-value">ReAct 循环</span>
              </div>
            </div>
            <div className="built-in-tools">
              <h4>内置工具</h4>
              <div className="tool-grid">
                {['read_file', 'write_file', 'edit_file', 'glob_search', 'grep_search', 'run_bash', 'fetch_url', 'web_search', 'code_search'].map(tool => (
                  <div key={tool} className="tool-chip">{tool}</div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="settings-panel">
            <div className="panel-header">
              <h3>Model Settings</h3>
            </div>

            {activeModelData && (
              <div className="active-model-banner">
                <span className="active-label">当前激活:</span>
                <span className="active-name">{activeModelData.name}</span>
              </div>
            )}

            <div className="model-list-section">
              {allModels.map(model => (
                <div
                  key={model.id}
                  className={`model-card ${model.id === activeModelId ? 'active' : ''}`}
                  onClick={() => setActiveModel(model.id)}
                >
                  <div className="model-header">
                    <span className="model-name">{model.name}</span>
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
                        onChange={(e) => {
                          e.stopPropagation()
                          updateModel(model.id, { temperature: parseFloat(e.target.value) })
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span>{model.temperature}</span>
                    </div>

                    <div className="param">
                      <label>Max Tokens</label>
                      <input
                        type="number"
                        value={model.maxTokens || 4096}
                        onChange={(e) => {
                          e.stopPropagation()
                          updateModel(model.id, { maxTokens: parseInt(e.target.value) })
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                  </div>

                  {(model.provider === ModelProvider.CUSTOM || model.provider === ModelProvider.OLLAMA) && (
                    <div className="model-fields">
                      {model.provider === ModelProvider.OLLAMA && (
                        <>
                          <input
                            type="text"
                            value={model.endpoint || 'http://localhost:11434'}
                            onChange={(e) => {
                              e.stopPropagation()
                              updateModel(model.id, { endpoint: e.target.value })
                            }}
                            placeholder="Ollama Endpoint"
                            className="model-field"
                            onClick={(e) => e.stopPropagation()}
                          />
                          <input
                            type="text"
                            value={model.model || ''}
                            onChange={(e) => {
                              e.stopPropagation()
                              updateModel(model.id, { model: e.target.value })
                            }}
                            placeholder="Model Name"
                            className="model-field"
                            onClick={(e) => e.stopPropagation()}
                          />
                        </>
                      )}
                      {model.provider === ModelProvider.CUSTOM && (
                        <>
                          <input
                            type="text"
                            value={model.endpoint || ''}
                            onChange={(e) => {
                              e.stopPropagation()
                              updateModel(model.id, { endpoint: e.target.value })
                            }}
                            placeholder="API Endpoint"
                            className="model-field"
                            onClick={(e) => e.stopPropagation()}
                          />
                          <input
                            type="password"
                            value={model.apiKey || ''}
                            onChange={(e) => {
                              e.stopPropagation()
                              updateModel(model.id, { apiKey: e.target.value })
                            }}
                            placeholder="API Key"
                            className="model-field"
                            onClick={(e) => e.stopPropagation()}
                          />
                        </>
                      )}
                    </div>
                  )}

                  <div className="model-actions">
                    <span className={`select-label ${model.id === activeModelId ? 'active' : ''}`}>
                      {model.id === activeModelId ? '✓ Active' : 'Click to select'}
                    </span>
                    {model.provider === ModelProvider.CUSTOM && (
                      <button
                        className="remove-btn"
                        onClick={(e) => {
                          e.stopPropagation()
                          removeModel(model.id)
                        }}
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
        )}
      </div>
    </aside>
  )
}

export default Sidebar
