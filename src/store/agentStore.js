import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import { AgentType, AgentStatus, MCPAction } from '../types'

export const useAgentStore = create((set, get) => ({
  agents: [],
  mainAgentId: null,
  subAgents: [],
  agentHierarchy: {},

  createMainAgent: (config = {}) => {
    const id = uuidv4()
    const agent = {
      id,
      type: AgentType.MAIN,
      name: 'Main Agent',
      status: AgentStatus.IDLE,
      systemPrompt: 'You are a helpful AI coding assistant. Coordinate with auxiliary agents to complete complex tasks.',
      modelId: 'gpt-4',
      tools: ['read', 'write', 'search', 'bash', 'web'],
      createdAt: Date.now(),
      messages: [],
      metadata: config.metadata || {}
    }
    set((state) => ({
      agents: [...state.agents, agent],
      mainAgentId: id,
      agentHierarchy: { ...state.agentHierarchy, [id]: [] }
    }))
    return id
  },

  spawnAgent: (type, config = {}) => {
    const { mainAgentId } = get()
    const id = uuidv4()
    const agentNames = {
      [AgentType.FILE]: 'File Agent',
      [AgentType.CODE]: 'Code Agent',
      [AgentType.BASH]: 'Bash Agent',
      [AgentType.WEB]: 'Web Agent',
      [AgentType.RESEARCH]: 'Research Agent',
      [AgentType.CUSTOM]: config.name || 'Custom Agent'
    }
    const agent = {
      id,
      type,
      name: agentNames[type] || config.name || 'Agent',
      status: AgentStatus.IDLE,
      parentId: config.parentId || mainAgentId,
      modelId: config.modelId || 'gpt-4',
      systemPrompt: config.systemPrompt || '',
      tools: config.tools || [],
      createdAt: Date.now(),
      messages: [],
      result: null,
      metadata: config.metadata || {}
    }
    set((state) => {
      const parentChildren = state.agentHierarchy[agent.parentId] || []
      return {
        agents: [...state.agents, agent],
        subAgents: [...state.subAgents, id],
        agentHierarchy: {
          ...state.agentHierarchy,
          [agent.parentId]: [...parentChildren, id]
        }
      }
    })
    return id
  },

  killAgent: (agentId, force = false) => {
    const { agents, agentHierarchy } = get()
    const agent = agents.find(a => a.id === agentId)
    if (!agent) return

    const killRecursive = (id) => {
      const children = agentHierarchy[id] || []
      children.forEach(childId => killRecursive(childId))
      set((state) => ({
        agents: state.agents.map(a => 
          a.id === id ? { ...a, status: AgentStatus.TERMINATED } : a
        ),
        subAgents: state.subAgents.filter(sa => sa !== id)
      }))
    }

    if (force) {
      const children = agentHierarchy[agentId] || []
      children.forEach(childId => killRecursive(childId))
    }

    set((state) => ({
      agents: state.agents.map(a => 
        a.id === agentId ? { ...a, status: AgentStatus.TERMINATED } : a
      ),
      subAgents: state.subAgents.filter(sa => sa !== agentId)
    }))
  },

  updateAgentStatus: (agentId, status) => set((state) => ({
    agents: state.agents.map(a =>
      a.id === agentId ? { ...a, status } : a
    )
  })),

  assignTask: (agentId, task) => set((state) => ({
    agents: state.agents.map(a =>
      a.id === agentId 
        ? { ...a, status: AgentStatus.WORKING, currentTask: task } 
        : a
    )
  })),

  setAgentResult: (agentId, result) => set((state) => ({
    agents: state.agents.map(a =>
      a.id === agentId 
        ? { ...a, status: AgentStatus.COMPLETED, result } 
        : a
    )
  })),

  addMessage: (agentId, message) => set((state) => ({
    agents: state.agents.map(a =>
      a.id === agentId 
        ? { ...a, messages: [...a.messages, message] }
        : a
    )
  })),

  getAgent: (agentId) => {
    const { agents } = get()
    return agents.find(a => a.id === agentId)
  },

  getMainAgent: () => {
    const { agents, mainAgentId } = get()
    return agents.find(a => a.id === mainAgentId)
  },

  getSubAgents: () => {
    const { agents, subAgents } = get()
    return agents.filter(a => subAgents.includes(a.id))
  },

  getChildAgents: (parentId) => {
    const { agents, agentHierarchy } = get()
    const childIds = agentHierarchy[parentId] || []
    return agents.filter(a => childIds.includes(a.id))
  },

  sendMCPMessage: (fromId, toId, action, payload) => {
    const message = {
      id: uuidv4(),
      from: fromId,
      to: toId,
      action,
      payload,
      timestamp: Date.now()
    }
    const { agents } = get()
    const targetAgent = agents.find(a => a.id === toId)
    if (targetAgent) {
      set((state) => ({
        agents: state.agents.map(a =>
          a.id === toId
            ? { ...a, messages: [...a.messages, { type: 'mcp', ...message }] }
            : a
        )
      }))
    }
    return message
  }
}))