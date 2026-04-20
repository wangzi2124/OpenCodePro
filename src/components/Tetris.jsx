import { useState, useEffect, useCallback, useRef } from 'react'
import './Tetris.css'

const SHAPES = {
  I: { shape: [[1, 1, 1, 1]], color: '#00f0f0' },
  O: { shape: [[1, 1], [1, 1]], color: '#f0f000' },
  T: { shape: [[0, 1, 0], [1, 1, 1]], color: '#a000f0' },
  S: { shape: [[0, 1, 1], [1, 1, 0]], color: '#00f000' },
  Z: { shape: [[1, 1, 0], [0, 1, 1]], color: '#f00000' },
  J: { shape: [[1, 0, 0], [1, 1, 1]], color: '#0000f0' },
  L: { shape: [[0, 0, 1], [1, 1, 1]], color: '#f0a000' }
}

const COLS = 10
const ROWS = 20

function createEmptyBoard() {
  return Array(ROWS).fill(null).map(() => Array(COLS).fill(0))
}

function Tetris() {
  const [board, setBoard] = useState(createEmptyBoard)
  const [currentPiece, setCurrentPiece] = useState(null)
  const [score, setScore] = useState(0)
  const [level, setLevel] = useState(1)
  const [gameOver, setGameOver] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [nextPiece, setNextPiece] = useState(null)
  const boardRef = useRef(null)
  const gameLoopRef = useRef(null)

  const getRandomPiece = useCallback(() => {
    const keys = Object.keys(SHAPES)
    const key = keys[Math.floor(Math.random() * keys.length)]
    return { ...SHAPES[key], key }
  }, [])

  const rotatePiece = useCallback((piece) => {
    const rotated = piece.shape[0].map((_, i) =>
      piece.shape.map(row => row[i]).reverse()
    )
    return { ...piece, shape: rotated }
  }, [])

  const isValidMove = useCallback((piece, newBoard, offsetX = 0, offsetY = 0) => {
    for (let y = 0; y < piece.shape.length; y++) {
      for (let x = 0; x < piece.shape[y].length; x++) {
        if (piece.shape[y][x]) {
          const newX = piece.x + x + offsetX
          const newY = piece.y + y + offsetY
          if (newX < 0 || newX >= COLS || newY >= ROWS) return false
          if (newY >= 0 && newBoard[newY][newX]) return false
        }
      }
    }
    return true
  }, [])

  const mergePiece = useCallback((piece, board) => {
    const newBoard = board.map(row => [...row])
    for (let y = 0; y < piece.shape.length; y++) {
      for (let x = 0; x < piece.shape[y].length; x++) {
        if (piece.shape[y][x]) {
          const boardY = piece.y + y
          const boardX = piece.x + x
          if (boardY >= 0) {
            newBoard[boardY][boardX] = piece.color
          }
        }
      }
    }
    return newBoard
  }, [])

  const clearLines = useCallback((board) => {
    let linesCleared = 0
    const newBoard = board.filter(row => row.some(cell => !cell))
    while (newBoard.length < ROWS) {
      newBoard.unshift(Array(COLS).fill(0))
      linesCleared++
    }
    if (linesCleared > 0) {
      setScore(prev => prev + linesCleared * 100 * linesCleared * level)
      setLevel(prev => Math.floor(linesCleared / 10) + prev)
    }
    return newBoard
  }, [level])

  const spawnPiece = useCallback(() => {
    const piece = nextPiece || getRandomPiece()
    const next = getRandomPiece()
    setNextPiece(next)
    
    const newPiece = {
      ...piece,
      x: Math.floor((COLS - piece.shape[0].length) / 2),
      y: 0
    }
    
    if (!isValidMove(newPiece, board)) {
      setGameOver(true)
      return false
    }
    
    setCurrentPiece(newPiece)
    return true
  }, [board, nextPiece, getRandomPiece, isValidMove])

  const movePiece = useCallback((direction) => {
    if (!currentPiece || gameOver || isPaused) return
    
    const offsets = {
      left: [-1, 0],
      right: [1, 0],
      down: [0, 1]
    }
    const [dx, dy] = offsets[direction] || [0, 1]
    
    if (isValidMove(currentPiece, board, dx, dy)) {
      setCurrentPiece(prev => ({ ...prev, x: prev.x + dx, y: prev.y + dy }))
    } else if (direction === 'down') {
      const newBoard = mergePiece(currentPiece, board)
      const clearedBoard = clearLines(newBoard)
      setBoard(clearedBoard)
      spawnPiece()
    }
  }, [currentPiece, board, gameOver, isPaused, isValidMove, mergePiece, clearLines, spawnPiece])

  const rotate = useCallback(() => {
    if (!currentPiece || gameOver || isPaused) return
    const rotated = rotatePiece(currentPiece)
    if (isValidMove(rotated, board)) {
      setCurrentPiece(rotated)
    }
  }, [currentPiece, board, gameOver, isPaused, isValidMove, rotatePiece])

  const restart = useCallback(() => {
    setBoard(createEmptyBoard())
    setScore(0)
    setLevel(1)
    setGameOver(false)
    setIsPaused(false)
    setNextPiece(null)
    spawnPiece()
  }, [spawnPiece])

  useEffect(() => {
    if (!currentPiece && !gameOver && board.every(row => row.every(cell => !cell))) {
      spawnPiece()
    }
  }, [])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (gameOver) return
      
      switch (e.key) {
        case 'ArrowLeft':
          movePiece('left')
          break
        case 'ArrowRight':
          movePiece('right')
          break
        case 'ArrowDown':
          movePiece('down')
          break
        case 'ArrowUp':
          rotate()
          break
        case ' ':
          setIsPaused(prev => !prev)
          break
        default:
          break
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [gameOver, movePiece, rotate])

  useEffect(() => {
    if (gameOver || isPaused || !currentPiece) return
    
    const dropSpeed = Math.max(100, 1000 - (level - 1) * 100)
    
    gameLoopRef.current = setInterval(() => {
      movePiece('down')
    }, dropSpeed)
    
    return () => clearInterval(gameLoopRef.current)
  }, [gameOver, isPaused, currentPiece, level, movePiece])

  const displayBoard = currentPiece ? mergePiece(currentPiece, board) : board

  return (
    <div className="tetris">
      <div className="tetris-game">
        <div className="tetris-board" ref={boardRef}>
          {displayBoard.map((row, y) => (
            <div key={y} className="tetris-row">
              {row.map((cell, x) => (
                <div
                  key={x}
                  className={`tetris-cell ${cell ? 'filled' : ''}`}
                  style={cell ? { backgroundColor: cell } : {}}
                />
              ))}
            </div>
          ))}
        </div>
        
        {gameOver && (
          <div className="tetris-overlay">
            <div className="tetris-message">
              <h2>游戏结束</h2>
              <p>得分: {score}</p>
              <button onClick={restart}>重新开始</button>
            </div>
          </div>
        )}
        
        {isPaused && !gameOver && (
          <div className="tetris-overlay">
            <div className="tetris-message">
              <h2>暂停</h2>
              <p>按空格键继续</p>
            </div>
          </div>
        )}
      </div>
      
      <div className="tetris-sidebar">
        <div className="tetris-score">
          <h3>得分</h3>
          <p>{score}</p>
        </div>
        
        <div className="tetris-level">
          <h3>等级</h3>
          <p>{level}</p>
        </div>
        
        <div className="tetris-next">
          <h3>下一个</h3>
          <div className="tetris-preview">
            {nextPiece && nextPiece.shape.map((row, y) => (
              <div key={y} className="tetris-preview-row">
                {row.map((cell, x) => (
                  <div
                    key={x}
                    className={`tetris-preview-cell ${cell ? 'filled' : ''}`}
                    style={cell ? { backgroundColor: nextPiece.color } : {}}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
        
        <div className="tetris-controls">
          <h3>操作说明</h3>
          <ul>
            <li>← → 移动</li>
            <li>↓ 加速下落</li>
            <li>↑ 旋转</li>
            <li>空格 暂停/继续</li>
          </ul>
        </div>
        
        <button className="tetris-restart" onClick={restart}>
          重新开始
        </button>
      </div>
    </div>
  )
}

export default Tetris