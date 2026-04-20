import { useState } from 'react'
import { useAgentStore, useModelStore, useRagStore } from '../store'
import { AgentType, AgentStatus, ModelProvider } from '../types'
import './Sidebar.css'

function Sidebar() {
  const [activeTab, setActiveTab] = useState('agents')
  const [showRagPanel, setShowRagPanel] = useState(false)
  
  const mainAgent = useAgentStore(state => state.getMainAgent())
  const subAgents = useAgentStore(state => state.getSubAgents())
  const spawnAgent = useAgentStore(state => state.spawnAgent)
  const killAgent = useAgentStore(state => state.killAgent)
  const documents = useRagStore(state => state.documents)
  
  const models = useModelStore(state => state.models)
  const customModels = useModelStore(state => state.customModels)
  const activeModelId = useModelStore(state => state.activeModelId)
  const setActiveModel = useModelStore(state => state.setActiveModel)
  const addModel = useModelStore(state => state.addModel)
  const updateModel = useModelStore(state => state.updateModel)
  const removeModel = useModelStore(state => state.removeModel)

  const allModels = [...models, ...customModels]
  
  const handleModelSelect = (modelId) => {
    setActiveModel(modelId)
  }

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

  const agentTypeIcons = {
    [AgentType.FILE]: '📁',
    [AgentType.CODE]: '💻',
    [AgentType.BASH]: 'terminal',
    [AgentType.WEB]: '🌐',
    [AgentType.RESEARCH]: '🔍'
  }

  const handleSpawnAgent = (type) => {
    if (mainAgent) {
      spawnAgent(type, { parentId: mainAgent.id })
    }
  }

  const tabs = [
    { id: 'agents', label: 'Agents', icon: '🤖' },
    { id: 'rag', label: 'RAG KB', icon: '📚' },
    { id: 'mcp', label: 'MCP', icon: '🔗' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`sidebar-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => {
              setActiveTab(tab.id)
              if (tab.id === 'rag') setShowRagPanel(true)
            }}
            title={tab.label}
          >
            <span className="tab-icon">{tab.icon}</span>
          </button>
        ))}
      </div>

      <div className="sidebar-content">
        {activeTab === 'agents' && (
          <div className="agents-panel">
            <div className="panel-header">
              <h3>Agents</h3>
            </div>
            
            <div className="agent-list">
              {mainAgent && (
                <div className="agent-item main-agent">
                  <span className="agent-icon">👑</span>
                  <div className="agent-info">
                    <span className="agent-name">{mainAgent.name}</span>
                    <span className={`agent-status ${mainAgent.status}`}>
                      {mainAgent.status}
                    </span>
                  </div>
                </div>
              )}

              {subAgents.map(agent => (
                <div key={agent.id} className="agent-item">
                  <span className="agent-icon">
                    {agentTypeIcons[agent.type] || '🤖'}
                  </span>
                  <div className="agent-info">
                    <span className="agent-name">{agent.name}</span>
                    <span className={`agent-status ${agent.status}`}>
                      {agent.status}
                    </span>
                  </div>
                  <button 
                    className="kill-btn"
                    onClick={() => killAgent(agent.id)}
                    title="Kill Agent"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            <div className="spawn-agents">
              <h4>Spawn Agent</h4>
              <div className="spawn-buttons">
                {Object.values(AgentType)
                  .filter(t => t !== AgentType.MAIN)
                  .map(type => (
                    <button
                      key={type}
                      className="spawn-btn"
                      onClick={() => handleSpawnAgent(type)}
                    >
                      {agentTypeIcons[type]} {type}
                    </button>
                  ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'mcp' && (
          <div className="mcp-panel">
            <div className="panel-header">
              <h3>MCP Protocol</h3>
            </div>
            <div className="mcp-info">
              <p>Model Communication Protocol</p>
              <div className="mcp-actions">
                <div className="mcp-action">
                  <code>SPAWN</code> - Create new agent
                </div>
                <div className="mcp-action">
                  <code>TASK</code> - Assign task
                </div>
                <div className="mcp-action">
                  <code>RESPONSE</code> - Return result
                </div>
                <div className="mcp-action">
                  <code>KILL</code> - Terminate agent
                </div>
                <div className="mcp-action">
                  <code>STATUS</code> - Check status
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="settings-panel">
            <div className="panel-header">
              <h3>Model Settings</h3>
            </div>
            
            <div className="model-list-section">
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
                      <label>Max Tokens</label>
                      <input
                        type="number"
                        value={model.maxTokens || 4096}
                        onChange={(e) => handleUpdateModel(model.id, 'maxTokens', parseInt(e.target.value))}
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
                            onChange={(e) => handleUpdateModel(model.id, 'endpoint', e.target.value)}
                            placeholder="Ollama Endpoint"
                            className="model-field"
                          />
                          <input
                            type="text"
                            value={model.model || ''}
                            onChange={(e) => handleUpdateModel(model.id, 'model', e.target.value)}
                            placeholder="Model Name"
                            className="model-field"
                          />
                        </>
                      )}
                      {model.provider === ModelProvider.CUSTOM && (
                        <>
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
                        </>
                      )}
                    </div>
                  )}
                  
                  <div className="model-actions">
                    <button
                      className={`select-btn ${model.id === activeModelId ? 'active' : ''}`}
                      onClick={() => handleModelSelect(model.id)}
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
        )}

        {activeTab === 'rag' && documents.length > 0 && (
          <div className="rag-summary">
            <div className="panel-header">
              <h3>Knowledge Base</h3>
            </div>
            <div className="rag-stats">
              <div className="stat">
                <span className="stat-value">{documents.length}</span>
                <span className="stat-label">Documents</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar