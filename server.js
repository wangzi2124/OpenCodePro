import express from 'express'
import cors from 'cors'
import { readFile, writeFile, readdir, stat } from 'fs/promises'
import { existsSync } from 'fs'
import { glob as globSync } from 'glob'
import { exec as execSync } from 'child_process'
import { promisify } from 'util'

const exec = promisify(execSync)
const app = express()

app.use(cors({
  origin: ['http://192.168.124.16:5173', 'http://localhost:5173'],
  credentials: true
}))

app.use(express.json())

app.post('/api/proxy/ollama', async (req, res) => {
  const endpoint = 'http://localhost:11434'
  const { path = '/api/chat', ...body } = req.body
  
  try {
    const response = await fetch(`${endpoint}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const data = await response.json()
    res.json(data)
  } catch (e) {
    res.json({ error: e.message })
  }
})

app.post('/api/proxy/openai', async (req, res) => {
  const { apiKey, ...body } = req.body
  if (!apiKey) return res.json({ error: 'API key required' })
  
  try {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify(body)
    })
    const data = await response.json()
    res.json(data)
  } catch (e) {
    res.json({ error: e.message })
  }
})

const tools = {
  async read({ filePath }) {
    if (!existsSync(filePath)) {
      return { error: `File not found: ${filePath}` }
    }
    const content = await readFile(filePath, 'utf-8')
    return { content }
  },

  async write({ filePath, content }) {
    const dir = filePath.substring(0, filePath.lastIndexOf('/'))
    if (dir && !existsSync(dir)) {
      return { error: `Directory not found: ${dir}` }
    }
    await writeFile(filePath, content, 'utf-8')
    return { success: true, message: `Written to ${filePath}` }
  },

  async edit({ filePath, oldString, newString }) {
    if (!existsSync(filePath)) {
      return { error: `File not found: ${filePath}` }
    }
    let content = await readFile(filePath, 'utf-8')
    if (!content.includes(oldString)) {
      return { error: 'oldString not found in file' }
    }
    content = content.replace(oldString, newString)
    await writeFile(filePath, content, 'utf-8')
    return { success: true, message: `Edited ${filePath}` }
  },

  async glob({ pattern }) {
    const files = await globSync(pattern)
    return { files }
  },

  async grep({ pattern, include = '*', path = '.' }) {
    try {
      const cmd = `grep -r --include="${include}" "${pattern}" "${path}" || true`
      const { stdout } = await exec(cmd)
      return { results: stdout.trim() || 'No matches found' }
    } catch (e) {
      return { results: 'No matches found' }
    }
  },

  async bash({ command, workdir }) {
    try {
      const cwd = workdir || process.cwd()
      
      let finalCommand = command
      let shell = '/bin/bash'
      
      if (process.platform === 'win32') {
        shell = 'cmd.exe'
        if (command.match(/^[A-Za-z]:/)) {
          const drive = command.charAt(0).toUpperCase()
          const rest = command.replace(/^[A-Za-z]:/, '').replace(/^\//, '').replace(/^\//, '')
          finalCommand = `${drive}:\\${rest}`
        }
      }

      const { stdout, stderr } = await exec(finalCommand, { 
        cwd,
        shell
      })
      return { 
        stdout: stdout || '(no output)', 
        stderr: stderr || '',
        success: true 
      }
    } catch (e) {
      return { 
        error: e.message,
        stderr: e.stderr || '',
        success: false 
      }
    }
  },

  async search({ query }) {
    return `Web search not implemented. Use fetch tool instead.`
  },

  async fetch({ url }) {
    try {
      const res = await fetch(url)
      const text = await res.text()
      return { content: text.substring(0, 50000) }
    } catch (e) {
      return { error: e.message }
    }
  }
}

app.post('/api/tool', async (req, res) => {
  const { tool, args } = req.body
  
  if (!tool || !tools[tool]) {
    return res.json({ error: `Unknown tool: ${tool}` })
  }

  try {
    const result = await tools[tool](args || {})
    res.json(result)
  } catch (e) {
    res.json({ error: e.message })
  }
})

app.get('/api/files', async (req, res) => {
  const { path } = req.query
  try {
    const files = await readdir(path || '.')
    const list = await Promise.all(
      files.slice(0, 100).map(async (f) => {
        const s = await stat(f)
        return { name: f, isDirectory: s.isDirectory(), size: s.size }
      })
    )
    res.json(list)
  } catch (e) {
    res.json({ error: e.message })
  }
})

const PORT = 3001
app.listen(PORT, () => {
  console.log(`Tool API server running on http://localhost:${PORT}`)
})