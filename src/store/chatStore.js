import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import { MessageRole } from '../types'
import { useRagStore } from './ragStore'
import { useModelStore } from './modelStore'

const SESSION_ID_KEY = 'opencode_session_id'

const loadSessionId = () => {
  let sid = localStorage.getItem(SESSION_ID_KEY)
  if (!sid) {
    sid = uuidv4()
    localStorage.setItem(SESSION_ID_KEY, sid)
  }
  return sid
}

export const useChatStore = create((set, get) => ({
  messages: [],
  isProcessing: false,
  pendingInput: null,
  abortController: null,
  agentMode: 'build',
  availableAgents: ['build', 'plan', 'explore', 'general'],
  sessionId: loadSessionId(),

  setSessionId: (sessionId) => {
    localStorage.setItem(SESSION_ID_KEY, sessionId)
    set({ sessionId })
  },

  newSession: () => {
    const newId = uuidv4()
    localStorage.setItem(SESSION_ID_KEY, newId)
    set({ sessionId: newId, messages: [] })
  },

  addMessage: (role, content, metadata = {}) => {
    const message = { id: uuidv4(), role, content, timestamp: Date.now(), metadata }
    set((state) => ({ messages: [...state.messages, message] }))
    return message
  },

  updateMessage: (messageId, updates) => set((state) => ({
    messages: state.messages.map(m => m.id === messageId ? { ...m, ...updates } : m)
  })),

  deleteMessage: (messageId) => set((state) => ({
    messages: state.messages.filter(m => m.id !== messageId)
  })),

  clearMessages: () => set({ messages: [] }),
  setProcessing: (isProcessing) => set({ isProcessing }),
  setAgentMode: (mode) => set({ agentMode: mode }),

  undoLastMessage: () => {
    const { messages } = get()
    const userMessages = messages.filter(m => m.role === MessageRole.USER)
    if (userMessages.length === 0) return null

    const lastUserMsg = userMessages[userMessages.length - 1]
    set((state) => ({
      messages: state.messages.filter(m => m.id !== lastUserMsg.id),
      pendingInput: lastUserMsg.content
    }))
    return lastUserMsg.content
  },

  getPendingInput: () => {
    const { pendingInput } = get()
    set({ pendingInput: null })
    return pendingInput
  },

  abortRequest: () => {
    const { abortController } = get()
    if (abortController) {
      abortController.abort()
      set({ abortController: null, isProcessing: false })
    }
  },

  sendMessage: async (content) => {
    const { addMessage, setProcessing, updateMessage } = get()

    const controller = new AbortController()
    set({ abortController: controller })

    addMessage(MessageRole.USER, content)
    setProcessing(true)

    const progressMsg = addMessage(MessageRole.ASSISTANT, '', {
      isProgress: true,
      steps: [],
      tools: [],
      currentTool: null
    })

    try {
      const ragStore = useRagStore.getState()
      const ragContext = await ragStore.getContext(content, 2000)
      const query = ragContext ? `${ragContext}\n\nUser query: ${content}` : content

      const modelStore = useModelStore.getState()
      const activeModel = modelStore.getActiveModel()
      const model = activeModel?.id || 'openai/gpt-4o'
      const apiKey = activeModel?.apiKey || null
      const endpointUrl = activeModel?.endpoint || 'https://openrouter.ai/api/v1'
      const isLocal = activeModel?.isLocal || false
      const { agentMode, sessionId } = get()

      const historyRes = await fetch(`/api/session/${sessionId}/history`)
      const historyData = historyRes.ok ? await historyRes.json() : { history: [] }
      const history = historyData.history || []

      const res = await fetch('/api/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          model,
          api_key: apiKey,
          endpoint: endpointUrl,
          is_local: isLocal,
          agent: agentMode,
          session_id: sessionId,
          history: history
        }),
        signal: controller.signal
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentText = ''
      let tools = []
      let steps = []
      let finalContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        
        const events = []
        let newlineIdx
        while ((newlineIdx = buffer.indexOf('\n\n')) !== -1) {
          const eventStr = buffer.slice(0, newlineIdx)
          buffer = buffer.slice(newlineIdx + 2)
          
          if (eventStr.startsWith('data: ')) {
            try {
              const event = JSON.parse(eventStr.slice(6))
              events.push(event)
            } catch (e) {
              console.error('Failed to parse SSE event:', e)
            }
          }
        }

        for (const event of events) {
          const { type, data } = event

          switch (type) {
            case 'start':
              updateMessage(progressMsg.id, {
                metadata: {
                  isProgress: true,
                  steps: [],
                  tools: [],
                  sessionId: data.session_id
                }
              })
              break

            case 'thought':
              steps.push({ type: 'thought', content: data.text || data })
              updateMessage(progressMsg.id, {
                metadata: { isProgress: false, steps: [...steps] }
              })
              break

            case 'tool-start':
              const toolInfo = {
                type: 'tool-start',
                tool: data.tool,
                args: data.args,
                callId: data.call_id,
                status: 'running'
              }
              tools.push(toolInfo)
              steps.push(toolInfo)
              updateMessage(progressMsg.id, {
                metadata: {
                  isProgress: false,
                  steps: [...steps],
                  tools: [...tools],
                  currentTool: data.tool
                }
              })
              break

            case 'tool-end':
              const toolEndInfo = {
                type: 'tool-end',
                tool: data.tool,
                callId: data.call_id,
                result: data.result,
                status: data.error ? 'error' : (data.status || 'completed'),
                error: data.error
              }
              const toolIndex = tools.findIndex(t => t.callId === data.call_id)
              if (toolIndex !== -1) {
                tools[toolIndex] = { ...tools[toolIndex], ...toolEndInfo }
              }
              steps.push(toolEndInfo)
              updateMessage(progressMsg.id, {
                metadata: {
                  isProgress: false,
                  steps: [...steps],
                  tools: [...tools],
                  currentTool: null
                }
              })
              break

            case 'tool-loop-complete':
              steps.push({ type: 'tool-loop', iteration: data.iteration })
              updateMessage(progressMsg.id, {
                metadata: { isProgress: true, steps: [...steps] }
              })
              break

            case 'text-delta':
              currentText += data.text || data
              updateMessage(progressMsg.id, {
                content: currentText,
                metadata: { isProgress: false }
              })
              break

            case 'retry':
              steps.push({ type: 'retry', reason: data.reason, delay: data.delay, attempt: data.attempt })
              updateMessage(progressMsg.id, {
                content: `Retrying (${data.attempt}): ${data.reason}...`,
                metadata: { isProgress: true, steps: [...steps] }
              })
              break

            case 'final-answer':
              finalContent = data.content || data
              currentText = finalContent
              updateMessage(progressMsg.id, {
                content: finalContent,
                metadata: {
                  isProgress: false,
                  steps: [...steps],
                  tools: [...tools],
                  finalAnswer: finalContent
                }
              })
              break

            case 'heartbeat':
              console.debug('[SSE] Heartbeat received')
              break

            case 'complete':
              console.log('[SSE] Stream complete')
              break

            case 'abort':
              updateMessage(progressMsg.id, {
                content: 'Request cancelled',
                metadata: { isProgress: false, isAborted: true }
              })
              break

            case 'error':
              updateMessage(progressMsg.id, {
                content: data.message || 'An error occurred',
                metadata: { isProgress: false, isError: true, errorType: data.type }
              })
              break

            case 'max-iterations':
              updateMessage(progressMsg.id, {
                content: data.accumulated || 'Max iterations reached',
                metadata: { isProgress: false, maxIterations: true }
              })
              break

            default:
              console.debug('[SSE] Unknown event type:', type)
          }
        }
      }

    } catch (error) {
      if (error.name === 'AbortError') {
        updateMessage(progressMsg.id, {
          content: 'Request cancelled',
          metadata: { isProgress: false, isAborted: true }
        })
      } else {
        console.error('Request error:', error)
        updateMessage(progressMsg.id, {
          content: `Error: ${error.message}`,
          metadata: { isProgress: false, isError: true }
        })
      }
    }

    setProcessing(false)
    set({ abortController: null })
  }
}))