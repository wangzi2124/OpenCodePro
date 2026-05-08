import './Header.css'

function Header({ model, onToggleTetris, showTetris, onNewSession }) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="logo">
          <span className="logo-icon">⚡</span>
          <span className="logo-text">OpenCode Pro</span>
        </div>
        <button className="new-session-btn" onClick={onNewSession} title="新建会话">
          + New
        </button>
      </div>

      <div className="header-center" />

      <div className="header-right">
        <div className="agent-status">
          <span className="status-dot idle" />
          <span className="status-text">ReAct Agent</span>
        </div>
        {model && (
          <div className="active-model">
            <span className="model-name">{model.name}</span>
          </div>
        )}
        <button className="tetris-toggle" onClick={onToggleTetris}>
          {showTetris ? '🎮' : '🎯'}
        </button>
      </div>
    </header>
  )
}

export default Header
