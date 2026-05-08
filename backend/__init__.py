from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import proxy
from .storage.storage_manager import StorageManager
from .config.config_manager import ConfigManager

app = FastAPI(title="OpenCode Pro Backend", version="1.0.0")

# 初始化存储
StorageManager.initialize()

# 加载配置
ConfigManager.load()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://192.168.124.16:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proxy.router, prefix="/api", tags=["agent"])


@app.get("/api/health")
async def health():
    tools = proxy.get_tools()
    config = ConfigManager.get()
    return {
        "status": "ok",
        "version": config.version,
        "tools": [t.name for t in tools],
        "agents": list(config.agents.keys())
    }


@app.get("/api/config")
async def get_config():
    """获取配置"""
    config = ConfigManager.get()
    return {
        "version": config.version,
        "agents": {name: {"model": a.model, "provider": a.provider} for name, a in config.agents.items()},
        "providers": list(config.providers.keys())
    }
