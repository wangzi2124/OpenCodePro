import { useState, useEffect } from 'react'
import { useModelStore, useChatStore } from '../store'
import './AgentPanel.css'

function AgentPanel() {
  const [activeTab, setActiveTab] = useState('config')
  const activeModelId = useModelStore(state => state.activeModelId)
  const getActiveModel = useModelStore(state => state.getActiveModel)
  const activeModel = getActiveModel()
  const agentMode = useChatStore(state => state.agentMode)
  const setAgentMode = useChatStore(state => state.setAgentMode)
  const availableAgents = useChatStore(state => state.availableAgents)
  
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    try {
      const res = await fetch('/api/agents')
      const data = await res.json()
      setAgents(data.agents || [])
    } catch (e) {
      console.error('Failed to fetch agents:', e)
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'config', label: 'Config' },
    { id: 'tools', label: 'Tools' },
    { id: 'agents', label: 'Agents' }
  ]

  const tools = [
    { name: 'read_file', desc: '读取文件内容', enabled: true },
    { name: 'write_file', desc: '写入文件内容', enabled: true },
    { name: 'edit_file', desc: '编辑文件（替换文本）', enabled: true },
    { name: 'glob_search', desc: '按模式查找文件', enabled: true },
    { name: 'grep_search', desc: '搜索文件内容', enabled: true },
    { name: 'run_bash', desc: '执行终端命令', enabled: true },
    { name: 'fetch_url', desc: '获取网页内容', enabled: true },
    { name: 'web_search', desc: '网络搜索', enabled: true },
    { name: 'agent_kill', desc: '终止 Agent', enabled: true }
  ]

  const getAgentInfo = (name) => {
    return agents.find(a => a.name === name) || {}
  }

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
        {activeTab === 'config' && (
          <div className="config-section">
            <div className="config-group">
              <label>Agent</label>
              <select
                value={agentMode}
                onChange={(e) => setAgentMode(e.target.value)}
                className="config-select"
              >
                {agents.map(agent => (
                  <option key={agent.name} value={agent.name}>
                    {agent.name} {agent.native ? '(native)' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div className="config-group">
              <label>Description</label>
              <input 
                type="text" 
                value={getAgentInfo(agentMode).description || 'No description'} 
                readOnly 
                className="config-input" 
              />
            </div>

            <div className="config-group">
              <label>Mode</label>
              <input 
                type="text" 
                value={getAgentInfo(agentMode).mode || 'primary'} 
                readOnly 
                className="config-input" 
              />
            </div>

            <div className="config-group">
              <label>Model</label>
              <input type="text" value={activeModel?.name || 'Not selected'} readOnly className="config-input" />
            </div>

            <div className="config-group">
              <label>Status</label>
              <span className="status-badge idle">就绪</span>
            </div>
          </div>
        )}

        {activeTab === 'tools' && (
          <div className="tools-section">
            <div className="tool-list">
              {tools.map(tool => (
                <div key={tool.name} className="tool-item">
                  <span className="tool-icon">{tool.enabled ? '✓' : '-'}</span>
                  <div className="tool-info">
                    <span className="tool-name">{tool.name}</span>
                    <span className="tool-desc">{tool.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'agents' && (
          <div className="agents-section">
            {loading ? (
              <div className="loading">Loading agents...</div>
            ) : (
              <div className="agent-list">
                {agents.map(agent => (
                  <div 
                    key={agent.name} 
                    className={`agent-card ${agentMode === agent.name ? 'active' : ''}`}
                    onClick={() => setAgentMode(agent.name)}
                  >
                    <div className="agent-card-header">
                      <span className="agent-card-name">{agent.name}</span>
                      {agent.default && <span className="default-badge">default</span>}
                    </div>
                    <div className="agent-card-desc">{agent.description || 'No description'}</div>
                    <div className="agent-card-meta">
                      <span className="agent-mode">{agent.mode}</span>
                      {agent.native && <span className="agent-native">native</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default AgentPanel