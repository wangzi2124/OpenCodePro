import { useState, useRef, useEffect } from 'react'
import './Terminal.css'

function Terminal() {
  const [output, setOutput] = useState([])
  const [input, setInput] = useState('')
  const outputRef = useRef(null)

  useEffect(() => {
    setOutput([
      { type: 'info', text: 'OpenCode Pro Terminal v1.0.0' },
      { type: 'info', text: 'ReAct Agent - Reasoning + Acting pattern' },
      { type: 'success', text: '9 tools registered and ready' },
      { type: 'info', text: 'Ready for commands...' }
    ])
  }, [])

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
    const [command] = cmd.split(' ')

    switch (command.toLowerCase()) {
      case 'help':
        return `Available commands:
  help    - Show this help
  status  - Show system status
  tools   - List registered tools
  clear   - Clear terminal`

      case 'status':
        return `System Status:
  Agent: ReAct Agent (ready)
  Tools: 9 registered
  Backend: FastAPI (localhost:3001)`

      case 'tools':
        return `Registered Tools:
  read_file, write_file, edit_file
  glob_search, grep_search
  run_bash
  fetch_url, web_search, code_search`

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
