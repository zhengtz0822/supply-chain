from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""

    # 应用信息
    APP_NAME: str = "Supply Chain API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./supply_chain.db"  # 默认使用 SQLite
    # DATABASE_URL: str = "postgresql://user:password@localhost/dbname"  # PostgreSQL 示例
    # DATABASE_URL: str = "mysql+pymysql://user:password@localhost/dbname"  # MySQL 示例

    # 数据库连接池配置
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # JWT 配置 (如果需要认证)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS 配置
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # DashScope API 配置 (用于 AgentScope)
    DASHSCOPE_API_KEY: str = "sk-48fcdafb9b374727baddb97b3b33c0d4"

    # 高德地图mcp地址
    AMAP_MCP_URL: str = ""
    # 高德地图APPKEY
    AMAP_APP_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
