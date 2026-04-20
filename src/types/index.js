export const ModelProvider = {
  OPENAI: 'openai',
  ANTHROPIC: 'anthropic',
  GEMINI: 'gemini',
  OLLAMA: 'ollama',
  CUSTOM: 'custom'
}

export const AgentType = {
  MAIN: 'main',
  FILE: 'file',
  CODE: 'code',
  BASH: 'bash',
  WEB: 'web',
  RESEARCH: 'research',
  EDIT: 'edit',
  GLOB: 'glob',
  GREP: 'grep',
  CUSTOM: 'custom'
}

export const AgentStatus = {
  IDLE: 'idle',
  WORKING: 'working',
  COMPLETED: 'completed',
  FAILED: 'failed',
  TERMINATED: 'terminated'
}

export const MCPAction = {
  SPAWN: 'spawn',
  TASK: 'task',
  RESPONSE: 'response',
  KILL: 'kill',
  STATUS: 'status'
}

export const MessageRole = {
  USER: 'user',
  ASSISTANT: 'assistant',
  AGENT: 'agent',
  SYSTEM: 'system'
}