import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import Terminal from './components/Terminal'
import AgentPanel from './components/AgentPanel'
import RAGPanel from './components/RAGPanel'
import Tetris from './components/Tetris'
import { useModelStore } from './store'
import './styles/index.css'

function App() {
  const [showTetris, setShowTetris] = useState(false)
  const getActiveModel = useModelStore(state => state.getActiveModel)
  const activeModel = getActiveModel()

  return (
    <div className="app">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#21262D',
            color: '#E6EDF3',
            border: '1px solid #30363D'
          }
        }}
      />

      <Header model={activeModel} onToggleTetris={() => setShowTetris(!showTetris)} showTetris={showTetris} />

      {showTetris ? (
        <Tetris />
      ) : (
        <div className="app-body">
          <Sidebar />

          <main className="main-content">
            <div className="chat-terminal-container">
              <ChatArea />
              <Terminal />
            </div>

            <AgentPanel />
          </main>
        </div>
      )}

      <RAGPanel />
    </div>
  )
}

export default App
