import { useState } from 'react'
import { useAgentStore, useModelStore } from '../store'
import { AgentStatus } from '../types'
import './AgentPanel.css'

function AgentPanel() {
  const [activeTab, setActiveTab] = useState('config')
  
  const agents = useAgentStore(state => state.agents)
  const mainAgent = useAgentStore(state => state.getMainAgent())
  const subAgents = useAgentStore(state => state.getSubAgents())
  const updateAgentStatus = useAgentStore(state => state.updateAgentStatus)
  const killAgent = useAgentStore(state => state.killAgent)
  const getActiveModel = useModelStore(state => state.getActiveModel)
  
  const activeModel = getActiveModel()

  const tabs = [
    { id: 'config', label: 'Config' },
    { id: 'memory', label: 'Memory' },
    { id: 'tools', label: 'Tools' }
  ]

  return (
    <div className="agent-panel">
      <div className="panel-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`panel-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="panel-content">
        {activeTab === 'config' && mainAgent && (
          <div className="config-section">
            <div className="config-group">
              <label>Name</label>
              <input 
                type="text" 
                value={mainAgent.name} 
                readOnly 
                className="config-input"
              />
            </div>
            
            <div className="config-group">
              <label>Model</label>
              <input 
                type="text" 
                value={activeModel?.name || 'Not selected'} 
                readOnly 
                className="config-input"
              />
            </div>
            
            <div className="config-group">
              <label>Status</label>
              <span className={`status-badge ${mainAgent.status}`}>
                {mainAgent.status}
              </span>
            </div>
            
            <div className="config-group">
              <label>System Prompt</label>
              <textarea 
                value={mainAgent.systemPrompt} 
                readOnly 
                className="config-textarea"
                rows={4}
              />
            </div>
          </div>
        )}

        {activeTab === 'memory' && (
          <div className="memory-section">
            <div className="memory-stats">
              <div className="stat-item">
                <span className="stat-label">Messages</span>
                <span className="stat-value">{mainAgent?.messages?.length || 0}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">SubAgents</span>
                <span className="stat-value">{subAgents.length}</span>
              </div>
            </div>
            
            {mainAgent?.messages?.length > 0 && (
              <div className="message-list">
                {mainAgent.messages.slice(-5).map((msg, i) => (
                  <div key={i} className="memory-message">
                    <span className="msg-type">{msg.type || 'msg'}</span>
                    <span className="msg-preview">
                      {typeof msg === 'string' ? msg.slice(0, 50) : JSON.stringify(msg).slice(0, 50)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'tools' && (
          <div className="tools-section">
            <div className="tool-list">
              {mainAgent?.tools?.map(tool => (
                <div key={tool} className="tool-item">
                  <span className="tool-icon">✓</span>
                  <span className="tool-name">{tool}</span>
                </div>
              ))}
            </div>
            
            <div className="available-tools">
              <h4>Available Tools</h4>
              <div className="tool-grid">
                {['read', 'write', 'search', 'bash', 'web', 'edit', 'glob', 'grep'].map(tool => (
                  <div 
                    key={tool} 
                    className={`tool-chip ${mainAgent?.tools?.includes(tool) ? 'enabled' : ''}`}
                  >
                    {tool}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="sub-agents-section">
        <h4>Active SubAgents ({subAgents.length})</h4>
        <div className="sub-agent-list">
          {subAgents.length === 0 ? (
            <p className="no-agents">No sub-agents running</p>
          ) : (
            subAgents.map(agent => (
              <div key={agent.id} className="sub-agent-card">
                <div className="sub-agent-header">
                  <span className="sub-agent-name">{agent.name}</span>
                  <span className={`sub-agent-status ${agent.status}`}>
                    {agent.status}
                  </span>
                </div>
                <div className="sub-agent-actions">
                  <button 
                    className="action-btn"
                    onClick={() => updateAgentStatus(agent.id, AgentStatus.IDLE)}
                  >
                    Reset
                  </button>
                  <button 
                    className="action-btn kill"
                    onClick={() => killAgent(agent.id)}
                  >
                    Kill
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default AgentPanel