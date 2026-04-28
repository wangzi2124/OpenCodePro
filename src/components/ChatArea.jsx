import { useState, useRef, useEffect } from 'react'
import { useChatStore, useAgentStore } from '../store'
import { MessageRole, AgentType } from '../types'
import ReactMarkdown from 'react-markdown'
import './ChatArea.css'

const agentPlaceholders = {
  [AgentType.MAIN]: 'Describe the task you want help with...',
  [AgentType.FILE]: 'Search for files by pattern...',
  [AgentType.CODE]: 'Ask about code structure, logic, or implementation...',
  [AgentType.BASH]: 'Enter command to execute...',
  [AgentType.WEB]: 'Search the web for information...',
  [AgentType.RESEARCH]: 'Research topic or find documentation...',
  [AgentType.EDIT]: 'Edit, refactor, or write code...',
  [AgentType.GLOB]: 'Find files matching pattern...',
  [AgentType.GREP]: 'Search for content in files...',
  [AgentType.CUSTOM]: 'Enter your request...'
}

function ChatArea() {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  
  const messages = useChatStore(state => state.messages)
  const isProcessing = useChatStore(state => state.isProcessing)
  const sendMessage = useChatStore(state => state.sendMessage)
  const pendingBashCommand = useChatStore(state => state.pendingBashCommand)
  const confirmBashCommand = useChatStore(state => state.confirmBashCommand)
  const rejectBashCommand = useChatStore(state => state.rejectBashCommand)
  
  const getMainAgent = useAgentStore(state => state.getMainAgent)
  const mainAgent = getMainAgent()
  const currentPlaceholder = mainAgent ? agentPlaceholders[mainAgent.type] || agentPlaceholders[AgentType.MAIN] : agentPlaceholders[AgentType.MAIN]

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || isProcessing) return
    
    const userInput = input.trim()
    setInput('')
    
    await sendMessage(userInput)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e)
    }
  }

  return (
    <div className="chat-area">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h2>Welcome to OpenCode Pro</h2>
            <p>Your AI-powered coding assistant with multi-agent collaboration</p>
            <div className="features">
              <div className="feature">
                <span>🤖</span>
                <span>Multiple Agent Types</span>
              </div>
              <div className="feature">
                <span>📚</span>
                <span>RAG Knowledge Base</span>
              </div>
              <div className="feature">
                <span>🔗</span>
                <span>MCP Protocol</span>
              </div>
              <div className="feature">
                <span>⚡</span>
                <span>Configurable Models</span>
              </div>
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <div className="message-header">
                <span className="message-role">
                  {msg.role === MessageRole.USER ? 'You' : 
                   msg.role === MessageRole.ASSISTANT ? 'Assistant' :
                   msg.role === MessageRole.AGENT ? msg.metadata?.agentType || 'Agent' : 'System'}
                </span>
                {msg.metadata?.modelId && (
                  <span className="message-model">{msg.metadata.modelId}</span>
                )}
              </div>
              <div className="message-content">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            </div>
          ))
        )}
        
        {isProcessing && (
          <div className="message processing">
            <div className="processing-indicator">
              <span>•</span>
              <span>•</span>
              <span>•</span>
            </div>
          </div>
        )}

        {pendingBashCommand && (
          <div className="message system bash-confirm">
            <div className="bash-confirm-content">
              <span>⚠️ 执行此命令？</span>
              <code>{pendingBashCommand.command}</code>
              <div className="bash-confirm-buttons">
                <button className="confirm-btn" onClick={confirmBashCommand}>确认执行</button>
                <button className="reject-btn" onClick={rejectBashCommand}>取消</button>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <form className="input-area" onSubmit={handleSubmit}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`${currentPlaceholder} (Enter to send, Shift+Enter for new line)`}
          disabled={isProcessing}
          rows={1}
        />
        <button 
          type="submit" 
          disabled={!input.trim() || isProcessing}
          className="send-btn"
        >
          ➤
        </button>
      </form>
    </div>
  )
}

export default ChatArea