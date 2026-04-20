import { useAgentStore } from '../store'
import './Header.css'

function Header({ model }) {
  const mainAgent = useAgentStore(state => state.getMainAgent())

  return (
    <header className="header">
      <div className="header-left">
        <div className="logo">
          <span className="logo-icon">⚡</span>
          <span className="logo-text">OpenCode Pro</span>
        </div>
      </div>

      <div className="header-center" />

      <div className="header-right">
        <div className="agent-status">
          <span 
            className={`status-dot ${mainAgent?.status || 'idle'}`}
          />
          <span className="status-text">
            {mainAgent?.name || 'Main Agent'}
          </span>
        </div>
      </div>
    </header>
  )
}

export default Header