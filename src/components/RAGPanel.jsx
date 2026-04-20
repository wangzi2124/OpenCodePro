import { useState } from 'react'
import { useRagStore } from '../store'
import './RAGPanel.css'

function RAGPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  
  const documents = useRagStore(state => state.documents)
  const chunks = useRagStore(state => state.chunks)
  const searchResults = useRagStore(state => state.searchResults)
  const isIndexing = useRagStore(state => state.isIndexing)
  const addDocument = useRagStore(state => state.addDocument)
  const removeDocument = useRagStore(state => state.removeDocument)
  const chunkDocument = useRagStore(state => state.chunkDocument)
  const semanticSearch = useRagStore(state => state.semanticSearch)
  const clearIndex = useRagStore(state => state.clearIndex)

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files)
    
    for (const file of files) {
      const content = await file.text()
      const docId = addDocument({
        name: file.name,
        content,
        type: file.type
      })
      
      chunkDocument(docId)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    await semanticSearch(searchQuery)
  }

  return (
    <>
      <button className="rag-trigger" onClick={() => setIsOpen(true)}>
        Open RAG Panel
      </button>
      
      {isOpen && (
        <div className="rag-overlay" onClick={() => setIsOpen(false)}>
          <div className="rag-panel" onClick={e => e.stopPropagation()}>
            <div className="rag-header">
              <h2>📚 RAG Knowledge Base</h2>
              <button className="rag-close" onClick={() => setIsOpen(false)}>×</button>
            </div>
            
            <div className="rag-search">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search knowledge base..."
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button onClick={handleSearch} disabled={!searchQuery.trim()}>
                Search
              </button>
            </div>
            
            {searchResults.length > 0 && (
              <div className="search-results">
                <h3>Search Results</h3>
                {searchResults.map(({ chunk, score }) => (
                  <div key={chunk.id} className="result-item">
                    <div className="result-score">Score: {score.toFixed(2)}</div>
                    <p>{chunk.content.slice(0, 200)}...</p>
                  </div>
                ))}
              </div>
            )}
            
            <div className="rag-stats">
              <div className="stat">
                <span className="stat-num">{documents.length}</span>
                <span className="stat-label">Documents</span>
              </div>
              <div className="stat">
                <span className="stat-num">{chunks.length}</span>
                <span className="stat-label">Chunks</span>
              </div>
              <div className="stat">
                <span className="stat-num">{searchResults.length}</span>
                <span className="stat-label">Results</span>
              </div>
            </div>
            
            <div className="rag-documents">
              <h3>Documents</h3>
              {documents.length === 0 ? (
                <div className="upload-zone">
                  <input
                    type="file"
                    id="file-upload"
                    multiple
                    onChange={handleFileUpload}
                    accept=".txt,.md,.js,.jsx,.ts,.tsx,.py,.json"
                  />
                  <label htmlFor="file-upload">
                    📁 Click to upload documents
                    <br />
                    <small>Supports: TXT, MD, JS, TS, PY, JSON</small>
                  </label>
                </div>
              ) : (
                <div className="doc-list">
                  {documents.map(doc => (
                    <div key={doc.id} className="doc-item">
                      <div className="doc-info">
                        <span className="doc-name">{doc.name}</span>
                        <span className="doc-meta">
                          {doc.chunkCount} chunks • {doc.size} chars
                        </span>
                      </div>
                      <button 
                        className="doc-delete"
                        onClick={() => removeDocument(doc.id)}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="rag-actions">
              <button 
                className="add-doc-btn"
                onClick={() => document.getElementById('file-upload').click()}
              >
                + Add Document
              </button>
              <button 
                className="clear-btn"
                onClick={clearIndex}
                disabled={documents.length === 0}
              >
                Clear All
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default RAGPanel