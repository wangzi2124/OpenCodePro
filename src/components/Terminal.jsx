import { useState, useRef, useEffect } from 'react'
import { useAgentStore } from '../store'
import './Terminal.css'

function Terminal() {
  const [output, setOutput] = useState([])
  const [input, setInput] = useState('')
  const outputRef = useRef(null)
  
  const subAgents = useAgentStore(state => state.getSubAgents())

  useEffect(() => {
    const logs = [
      { type: 'info', text: 'OpenCode Pro Terminal v1.0.0' },
      { type: 'system', text: 'Main agent initialized' },
      { type: 'success', text: `Connected to ${subAgents.length} auxiliary agents` },
      { type: 'info', text: 'Ready for commands...' }
    ]
    setOutput(logs)
  }, [])

  useEffect(() => {
    if (subAgents.length > 0) {
      setOutput(prev => [...prev, { 
        type: 'agent', 
        text: `Agent spawned: ${subAgents[subAgents.length - 1].name}` 
      }])
    }
  }, [subAgents])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim()) return

    const cmd = input.trim()
    setOutput(prev => [...prev, { type: 'command', text: `$ ${cmd}` }])
    setInput('')

    setTimeout(() => {
      const response = executeCommand(cmd)
      if (response) {
        setOutput(prev => [...prev, { type: 'response', text: response }])
      }
    }, 100)
  }

  const executeCommand = (cmd) => {
    const [command, ...args] = cmd.split(' ')
    
    switch (command.toLowerCase()) {
      case 'help':
        return `Available commands:
  help          - Show this help
  agents        - List all agents
  kill <id>     - Kill agent by ID
  status       - Show system status
  clear        - Clear terminal`
      
      case 'agents':
        if (subAgents.length === 0) return 'No auxiliary agents running'
        return subAgents
          .map(a => `${a.id.slice(0, 8)} - ${a.name} (${a.status})`)
          .join('\n')
      
      case 'status':
        return `System Status:
  Main Agent: Active
  SubAgents: ${subAgents.length}
  Memory: ${(performance.memory?.usedJSHeapSize / 1024 / 1024 || 0).toFixed(1)} MB`
      
      case 'clear':
        setOutput([])
        return null
      
      default:
        return `Command not found: ${command}`
    }
  }

  const getTypeClass = (type) => {
    const classes = {
      info: 'term-info',
      system: 'term-system',
      success: 'term-success',
      error: 'term-error',
      warning: 'term-warning',
      agent: 'term-agent',
      command: 'term-command',
      response: 'term-response'
    }
    return classes[type] || ''
  }

  return (
    <div className="terminal">
      <div className="terminal-header">
        <span className="terminal-title">Terminal</span>
        <div className="terminal-controls">
          <button className="term-btn minimize">─</button>
          <button className="term-btn maximize">□</button>
          <button className="term-btn close">×</button>
        </div>
      </div>
      
      <div className="terminal-output" ref={outputRef}>
        {output.map((line, i) => (
          <div key={i} className={`terminal-line ${getTypeClass(line.type)}`}>
            {line.text}
          </div>
        ))}
      </div>
      
      <form className="terminal-input" onSubmit={handleSubmit}>
        <span className="prompt">$</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type command..."
          spellCheck={false}
        />
      </form>
    </div>
  )
}

export default Terminal