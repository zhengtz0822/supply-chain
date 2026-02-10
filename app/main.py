from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.tools.tool_registry import initialize_tools
import logging
import agentscope
from app.core.config import get_settings
from app.core.database import init_db
from app.routers import example
from app.routers import address
from app.routers import logistics

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    # 初始化 MCP 工具
    await initialize_tools()

    # 初始化智能体
    agentscope.init()
    yield
    # 关闭时执行
    print("Shutting down application...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Supply Chain Management API",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(example.router, prefix="/api/v1")
app.include_router(address.router, prefix="/api/v1")
app.include_router(logistics.router, prefix="/api/v1")


# 根路径
@app.get("/")
def root():
    return {
        "message": "Welcome to Supply Chain API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


# 健康检查
@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
