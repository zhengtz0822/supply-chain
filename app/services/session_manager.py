# services/session_manager.py
"""
会话管理器 - 负责多轮对话上下文持久化

使用 AgentScope 的 AsyncSQLAlchemyMemory 实现会话记忆的数据库存储，
支持跨请求的上下文保持。
"""
import logging
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from agentscope.memory import AsyncSQLAlchemyMemory, InMemoryMemory
from agentscope.message import Msg

logger = logging.getLogger(__name__)


class SessionManager:
    """
    会话管理器

    职责:
    - 管理用户会话的记忆存储
    - 为每个 session_id 提供独立的上下文
    - 支持 Redis 缓存 + 数据库持久化的双层架构（预留）
    """

    # 单例模式
    _instance: Optional['SessionManager'] = None
    _engine: Optional[AsyncEngine] = None
    _sessions: Dict[str, AsyncSQLAlchemyMemory] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化会话管理器"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._engine = None
            self._sessions = {}
            logger.info("[SessionManager] 会话管理器初始化完成")

    async def initialize(self, db_url: str = "sqlite+aiosqlite:///./supply_chain_memory.db"):
        """
        初始化数据库引擎

        Args:
            db_url: 数据库连接字符串
        """
        if self._engine is None:
            self._engine = create_async_engine(db_url, echo=False)
            logger.info(f"[SessionManager] 数据库引擎已创建: {db_url}")

    async def get_session_memory(self, session_id: str, user_id: str = "default") -> AsyncSQLAlchemyMemory:
        """
        获取或创建会话记忆

        Args:
            session_id: 会话ID
            user_id: 用户ID（默认为 "default"）

        Returns:
            该会话的记忆对象
        """
        # 确保引擎已初始化
        if self._engine is None:
            await self.initialize()

        # 检查缓存中是否已存在
        cache_key = f"{user_id}:{session_id}"
        if cache_key in self._sessions:
            return self._sessions[cache_key]

        # 创建新的会话记忆
        memory = AsyncSQLAlchemyMemory(
            engine_or_session=self._engine,
            user_id=user_id,
            session_id=session_id,
        )
        self._sessions[cache_key] = memory
        logger.info(f"[SessionManager] 创建新会话记忆: {cache_key}")
        return memory

    async def add_message(self, session_id: str, msg: Msg, user_id: str = "default"):
        """
        向会话中添加消息

        Args:
            session_id: 会话ID
            msg: 消息对象
            user_id: 用户ID
        """
        memory = await self.get_session_memory(session_id, user_id)
        await memory.add(msg)
        logger.debug(f"[SessionManager] 消息已添加到会话 {session_id}: {msg.name}")

    async def get_session_history(self, session_id: str, user_id: str = "default") -> list[Msg]:
        """
        获取会话历史记录

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            消息列表
        """
        memory = await self.get_session_memory(session_id, user_id)
        history = await memory.get_memory()
        logger.debug(f"[SessionManager] 获取会话 {session_id} 历史，共 {len(history)} 条消息")
        return history

    async def clear_session(self, session_id: str, user_id: str = "default"):
        """
        清除会话记忆

        Args:
            session_id: 会话ID
            user_id: 用户ID
        """
        memory = await self.get_session_memory(session_id, user_id)
        await memory.drop()
        cache_key = f"{user_id}:{session_id}"
        if cache_key in self._sessions:
            del self._sessions[cache_key]
        logger.info(f"[SessionManager] 会话已清除: {cache_key}")

    async def close_all(self):
        """关闭所有会话连接"""
        for memory in self._sessions.values():
            await memory.close()
        self._sessions.clear()
        if self._engine:
            await self._engine.dispose()
        logger.info("[SessionManager] 所有会话连接已关闭")


# 全局单例
session_manager = SessionManager()
