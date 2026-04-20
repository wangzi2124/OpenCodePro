# OpenCode Pro

开发者AI助手界面 - 使用AI代理帮助你完成软件开发任务。

## 快速开始

```bash
npm install
npm run dev
```

访问 http://localhost:5173

---

# OpenCodePro AI Agent 系统操作指南

本指南详细说明如何使用 OpenCodePro 的 AI Agent 系统来帮助你编写代码。

## 1. 模型配置

### 使用 Ollama 模型 (推荐)

如果你有本地 Ollama 服务：

1. **启动 Ollama 服务**
   ```bash
   ollama serve
   ```

2. **下载 CodeLlama 模型** (首次使用)
   ```bash
   ollama pull codellama
   ```

3. **在 OpenCodePro 中设置**
   - 点击右上角的 **Open Model Settings** 按钮
   - 找到 **CodeLlama (Ollama)** 模型
   - 确保 Endpoint 设置为 `http://localhost:11434`
   - 点击 **Select** 激活该模型

### 使用 OpenAI/GPT 模型

1. 获取 API Key: https://platform.openai.com/api-keys
2. 在 Model Settings 中添加自定义模型
3. 输入 Endpoint 和 API Key

## 2. 与 AI 对话

在 ChatArea 中输入你的需求，例如：

```
请用 React 写一个俄罗斯方块游戏，包含计分系统和等级系统
```

AI 会自动协调不同类型的 Agent 来完成你的任务：
- **FILE Agent** - 文件操作
- **CODE Agent** - 代码编写
- **BASH Agent** - 终端命令
- **WEB Agent** - 网页获取
- **RESEARCH Agent** - 研究搜索

## 3. 运行生成的项目

1. 进入项目目录
   ```bash
   cd D:\TetrisGame
   ```

2. 安装依赖
   ```bash
   npm install
   ```

3. 启动开发服务器
   ```bash
   npm run dev
   ```

---

## 项目成果

已在 **D:\TetrisGame** 创建俄罗斯方块游戏：

| 文件 | 说明 |
|------|------|
| `package.json` | 项目配置 |
| `vite.config.js` | Vite 构建配置 |
| `index.html` | 入口 HTML |
| `src/App.jsx` | 游戏主组件 |
| `src/main.jsx` | React 入口 |
| `src/index.css` | 游戏样式 |
| `README.md` | 项目说明 |

### 运行游戏

```bash
cd D:\TetrisGame
npm run dev
```

访问 http://localhost:5174

### 游戏操作

| 按键 | 功能 |
|------|------|
| ← → | 左右移动 |
| ↓ | 加速下落 |
| ↑ | 旋转 |
| 空格 | 暂停/继续 |

---

## 技术栈

- React 18 + Vite 5
- Zustand (状态管理)
- CSS Variables (深色主题)

## 项目结构

```
src/
├── components/   # Header, Sidebar, ChatArea, Terminal, AgentPanel, ModelModal, RAGPanel, Tetris
├── store/       # Zustand stores
├── types/       # 类型定义
├── styles/      # 全局样式
├── App.jsx      # 主入口
└── main.jsx     # React入口
```

## 命令

```bash
npm run dev       # 开发服务器
npm run build     # 构建生产版本
npm run preview   # 预览生产版本
```

## Windows注意事项

- 创建目录: `New-Item -ItemType Directory`
- 避免使用 `&&` - 使用分号或换行