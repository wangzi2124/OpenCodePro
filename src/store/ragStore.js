import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'

export const useRagStore = create((set, get) => ({
  documents: [],
  chunks: [],
  index: [],
  searchResults: [],
  isIndexing: false,

  addDocument: (document) => {
    const id = uuidv4()
    const doc = {
      id,
      name: document.name,
      content: document.content,
      type: document.type || 'text',
      size: document.content.length,
      uploadedAt: Date.now(),
      chunkCount: 0,
      metadata: document.metadata || {}
    }
    set((state) => ({
      documents: [...state.documents, doc]
    }))
    return id
  },

  removeDocument: (docId) => set((state) => ({
    documents: state.documents.filter(d => d.id !== docId),
    chunks: state.chunks.filter(c => c.documentId !== docId)
  })),

  chunkDocument: (docId, chunkSize = 500, overlap = 50) => {
    const { documents, chunkDocument: chunkFn } = get()
    const doc = documents.find(d => d.id === docId)
    if (!doc) return

    const text = doc.content
    const chunks = []
    for (let i = 0; i < text.length; i += chunkSize - overlap) {
      const chunk = text.slice(i, i + chunkSize)
      chunks.push({
        id: uuidv4(),
        documentId: docId,
        content: chunk,
        index: i,
        embedding: null,
        metadata: { ...doc.metadata, position: chunks.length }
      })
      if (i + chunkSize >= text.length) break
    }

    set((state) => ({
      chunks: [...state.chunks, ...chunks],
      documents: state.documents.map(d =>
        d.id === docId ? { ...d, chunkCount: chunks.length } : d
      )
    }))
    return chunks
  },

  addToIndex: async (chunkId, embedding) => {
    set((state) => ({
      index: [...state.index, { chunkId, embedding }]
    }))
  },

  semanticSearch: async (query, topK = 5) => {
    const { chunks } = get()
    if (chunks.length === 0) return []

    const queryLower = query.toLowerCase()
    const results = chunks
      .map(chunk => ({
        chunk,
        score: calculateSimilarity(queryLower, chunk.content.toLowerCase())
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, topK)
      .filter(r => r.score > 0.1)

    set({ searchResults: results })
    return results
  },

  getContext: async (query, maxTokens = 2000) => {
    const results = await get().semanticSearch(query, 10)
    let context = ''
    let tokenCount = 0

    for (const { chunk, score } of results) {
      const chunkTokens = chunk.content.split(/\s+/).length
      if (tokenCount + chunkTokens > maxTokens) break
      context += `[${score.toFixed(2)}] ${chunk.content}\n\n`
      tokenCount += chunkTokens
    }

    return context
  },

  clearIndex: () => set({ documents: [], chunks: [], index: [], searchResults: [] })
}))

function calculateSimilarity(query, text) {
  const queryWords = new Set(query.split(/\s+/).filter(w => w.length > 2))
  const textWords = text.split(/\s+/)
  let matchCount = 0

  for (const word of textWords) {
    if (queryWords.has(word)) matchCount++
  }

  return queryWords.size > 0 ? matchCount / queryWords.size : 0
}