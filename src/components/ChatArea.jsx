import { useState, useRef, useEffect } from 'react'
import { useChatStore } from '../store'
import { MessageRole } from '../types'
import ReactMarkdown from 'react-markdown'
import './ChatArea.css'

function ChatArea() {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const [loaded, setLoaded] = useState(false)

  const messages = useChatStore(state => state.messages)
  const isProcessing = useChatStore(state => state.isProcessing)
  const sendMessage = useChatStore(state => state.sendMessage)
  const undoLastMessage = useChatStore(state => state.undoLastMessage)
  const getPendingInput = useChatStore(state => state.getPendingInput)
  const sessionId = useChatStore(state => state.sessionId)
  const addMessage = useChatStore(state => state.addMessage)

  useEffect(() => {
    if (loaded || !sessionId) return

    const loadHistory = async () => {
      try {
        const res = await fetch(`/api/session/${sessionId}/history`)
        const data = await res.json()
        const history = data.history || []

        for (const msg of history) {
          const role = msg.role === 'user' ? MessageRole.USER : MessageRole.ASSISTANT
          addMessage(role, msg.content, { finalAnswer: msg.content })
        }
        setLoaded(true)
      } catch (e) {
        console.error('Failed to load history:', e)
        setLoaded(true)
      }
    }

    loadHistory()
  }, [sessionId])

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

  const handleUndo = () => {
    const { abortRequest, undoLastMessage } = useChatStore.getState()
    abortRequest()
    const content = undoLastMessage()
    if (content) {
      setInput(content)
    }
  }

  const formatToolArgs = (args) => {
    if (!args) return ''
    try {
      return JSON.stringify(args, null, 2)
    } catch {
      return String(args)
    }
  }

  const renderToolCall = (step, isRunning = false) => {
    if (step.type === 'tool-start') {
      return (
        <div className="tool-call running">
          <span className="tool-badge">🔧</span>
          <span className="tool-name">{step.tool}</span>
          <div className="tool-args">
            <pre>{formatToolArgs(step.args)}</pre>
          </div>
        </div>
      )
    }
    
    if (step.type === 'tool-end') {
      const statusIcon = step.error ? '❌' : '✅'
      return (
        <div className={`tool-call ${step.error ? 'error' : 'completed'}`}>
          <span className="tool-badge">{statusIcon}</span>
          <span className="tool-name">{step.tool}</span>
          {step.result && (
            <div className="tool-result">
              <pre>{String(step.result).slice(0, 500)}{step.result?.length > 500 ? '...' : ''}</pre>
            </div>
          )}
        </div>
      )
    }
    
    return null
  }

  const renderMessageContent = (msg) => {
    const { steps, tasks, isError, isAborted, currentTool, tools } = msg.metadata || {}

    if (isError) {
      return (
        <div className="error-content">
          <span className="error-icon">⚠️</span>
          {msg.content}
        </div>
      )
    }

    if (isAborted) {
      return (
        <div className="aborted-content">
          <span className="abort-icon">⏹️</span>
          {msg.content}
        </div>
      )
    }

    if (msg.content === '' && isProcessing) {
      return (
        <div className="thinking-indicator">
          <div className="thinking-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
          {currentTool ? (
            <span className="thinking-text">执行 {currentTool}...</span>
          ) : (
            <span className="thinking-text">Agent 正在思考...</span>
          )}
        </div>
      )
    }

    if (tasks && tasks.length > 0) {
      const completedTasks = steps.filter(s => s.type === 'task_complete').length
      const errorTasks = steps.filter(s => s.type === 'task_error').length

      return (
        <div className="plan-response">
          <div className="plan-header">
            <span className="plan-badge">📋 计划</span>
            <span className="plan-count">
              {completedTasks}/{tasks.length} 完成
              {errorTasks > 0 && <span className="error-count"> ({errorTasks} 失败)</span>}
            </span>
          </div>
          <div className="task-list">
            {tasks.map((task, idx) => {
              const startStep = steps.find(s => s.taskId === task.id && s.type === 'task_start')
              const completeStep = steps.find(s => s.taskId === task.id && s.type === 'task_complete')
              const errorStep = steps.find(s => s.taskId === task.id && s.type === 'task_error')

              return (
                <div key={idx} className={`task-item ${completeStep ? 'completed' : ''} ${errorStep ? 'error' : ''}`}>
                  <span className="task-checkbox">
                    {completeStep ? '✓' : errorStep ? '✗' : startStep ? '▶' : '○'}
                  </span>
                  <span className="task-id">#{task.id}</span>
                  <span className="task-desc">{task.description}</span>
                  {completeStep && (
                    <div className="task-result-inline">{completeStep.content?.slice(0, 100)}...</div>
                  )}
                  {errorStep && (
                    <div className="task-error-inline">{errorStep.content}</div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )
    }

    if (!steps || steps.length === 0) {
      return <ReactMarkdown>{msg.content}</ReactMarkdown>
    }

    return (
      <div className="agent-response">
        {steps.map((step, stepIdx) => {
          if (step.type === 'tool-start' || step.type === 'tool-end') {
            return (
              <div key={stepIdx} className="step-item tool-step">
                {renderToolCall(step)}
              </div>
            )
          }

          return (
            <div key={stepIdx} className={`step-item ${step.type}`}>
              <details open={step.type === 'observation' || step.type === 'tool-end'}>
                <summary>
                  {step.type === 'thought' && '💭 Thinking'}
                  {step.type === 'action' && '⚡ Action'}
                  {step.type === 'observation' && '👁️ Observation'}
                  {step.type === 'retry' && '🔄 Retrying'}
                  {step.type === 'tool-loop' && `🔧 Tool Loop (${step.iteration})`}
                </summary>
                <div className="step-content">
                  {step.type === 'retry' && (
                    <p>{step.reason} (等待 {step.delay}s)</p>
                  )}
                  {step.type === 'observation' || step.type === 'tool-end' ? (
                    <pre className="observation-code">{step.content || step.result || ''}</pre>
                  ) : step.type === 'action' ? (
                    <code className="action-code">{step.content}</code>
                  ) : (
                    <p>{step.content}</p>
                  )}
                </div>
              </details>
            </div>
          )
        })}
        {msg.content && (
          <div className="final-answer">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="chat-area">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h2>🚀 OpenCode Pro</h2>
            <p>流式 AI 编程助手 - 实时响应所见即所得</p>
            <div className="features">
              <div className="feature">
                <span>🔄</span>
                <span>实时流式响应</span>
              </div>
              <div className="feature">
                <span>🛠️</span>
                <span>智能工具调用</span>
              </div>
              <div className="feature">
                <span>📝</span>
                <span>自动代码编辑</span>
              </div>
              <div className="feature">
                <span>🔍</span>
                <span>项目上下文理解</span>
              </div>
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <div className="message-header">
                <span className="message-role">
                  {msg.role === MessageRole.USER ? '👤 You' : '🤖 Agent'}
                </span>
                {msg.metadata?.sessionId && (
                  <span className="message-session">Session: {msg.metadata.sessionId.slice(0, 8)}</span>
                )}
              </div>
              <div className="message-content">
                {renderMessageContent(msg)}
              </div>
            </div>
          ))
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-area" onSubmit={handleSubmit}>
        <button
          type="button"
          onClick={handleUndo}
          className="undo-btn"
          title="撤销上一条消息"
          disabled={messages.length === 0}
        >
          ↩
        </button>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入任务描述，Agent 将实时响应... (Enter 发送, Shift+Enter 换行)"
          disabled={isProcessing}
          rows={1}
        />
        <button
          type="submit"
          disabled={!input.trim() || isProcessing}
          className="send-btn"
        >
          {isProcessing ? '⏳' : '➤'}
        </button>
      </form>
    </div>
  )
}

export default ChatArea