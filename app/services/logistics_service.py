# services/logistics_service.py
"""
物流跟踪服务 - 使用多Agent架构处理物流对话

架构设计:
- Perceiver (感知智能体): 识别图片、提取关键信息
- Reasoner (推理智能体): 理解意图、规划执行步骤
- Actor (执行智能体): 执行业务操作
- Dialog (对话智能体): 生成用户友好的回复

使用 MsgHub 模式实现多Agent协作和通信
"""
import logging
import json
from typing import Dict, Any, Optional, List
from agentscope.message import Msg
from app.core.config import get_settings
from agentscope.pipeline import MsgHub
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.formatter import DashScopeMultiAgentFormatter
from agentscope.memory import InMemoryMemory

from app.services.session_manager import session_manager
from app.agents.logistics_perception_agent import LogisticsPerceptionAgent
from app.agents.logistics_reasoning_agent import LogisticsReasoningAgent
from app.agents.logistics_action_agent import LogisticsActionAgent
from app.agents.logistics_dialog_agent import LogisticsDialogAgent

logger = logging.getLogger(__name__)


class LogisticsService:
    """
    物流跟踪服务

    职责:
    1. 初始化和管理多Agent系统
    2. 协调各Agent之间的通信
    3. 处理用户请求并返回结果
    4. 管理会话上下文持久化
    """

    # 类变量，存储Agent实例（单例模式）
    _perceiver: Optional[LogisticsPerceptionAgent] = None
    _reasoner: Optional[LogisticsReasoningAgent] = None
    _actor: Optional[LogisticsActionAgent] = None
    _dialog: Optional[LogisticsDialogAgent] = None
    _initialized = False

    @classmethod
    async def initialize(cls):
        """
        初始化所有Agent

        应在应用启动时调用一次
        """
        if cls._initialized:
            return

        logger.info("[LogisticsService] 开始初始化多Agent系统...")

        # 获取模型配置（从环境变量或配置文件）
        import os
        import agentscope
        api_key =get_settings().DASHSCOPE_API_KEY
        agentscope.init(studio_url="http://localhost:3000")
        # 创建模型配置
        model_config = DashScopeChatModel(
            model_name="qwen-plus",
            api_key=api_key,
            stream=False,
        )

        # 创建格式化器
        # DialogAgent 使用单智能体格式化器
        single_formatter = DashScopeChatFormatter()
        # 其他Agent使用多智能体格式化器（因为会在MsgHub中通信）
        multi_formatter = DashScopeMultiAgentFormatter()

        # 初始化各Agent
        cls._perceiver = LogisticsPerceptionAgent(
            model_config=model_config,
            formatter=multi_formatter,
            memory=InMemoryMemory(),
        )

        cls._reasoner = LogisticsReasoningAgent(
            model_config=model_config,
            formatter=multi_formatter,
            memory=InMemoryMemory(),
        )

        cls._actor = LogisticsActionAgent()

        cls._dialog = LogisticsDialogAgent(
            model_config=model_config,
            formatter=single_formatter,
            memory=InMemoryMemory(),
        )

        cls._initialized = True
        logger.info("[LogisticsService] 多Agent系统初始化完成")

    @staticmethod
    def _extract_user_text(content: List) -> str:
        """
        从用户输入中提取文本内容

        Args:
            content: 用户输入的内容列表

        Returns:
            提取的文本内容
        """
        texts = []
        for item in content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif item.get("type") == "image_url":
                texts.append(f"[图片: {item.get('image_url', '')}]")
            elif item.get("type") == "image":
                texts.append("[图片: base64编码]")
        return " ".join(texts)

    @staticmethod
    def _extract_text_from_msg(msg: Msg) -> str:
        """
        从 Msg 对象中提取文本内容

        Args:
            msg: AgentScope 消息对象

        Returns:
            提取的文本内容
        """
        content = msg.content

        # 如果是字符串，直接返回
        if isinstance(content, str):
            return content

        # 如果是列表（content blocks），提取所有文本
        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                elif hasattr(block, "type"):
                    # ContentBlock 对象
                    if block.type == "text":
                        texts.append(getattr(block, "text", ""))
            return "\n".join(texts)

        # 其他情况转为字符串
        return str(content)

    @staticmethod
    async def ordertalk(session_id: str, content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        物流订单对话处理入口

        工作流程:
        1. 感知智能体提取关键信息（单号、地址等）
        2. 推理智能体分析意图、规划步骤
        3. 执行智能体执行业务操作
        4. 对话智能体生成用户友好的回复

        Args:
            session_id: 会话ID，用于多轮对话上下文管理
            content: 用户输入内容列表，支持 text/image_url/image

        Returns:
            {
                'success': True/False,
                'message': '回复给用户的文本',
                'data': {...},  # 可选的额外数据
            }
        """
        logger.info(f"[LogisticsService] ordertalk 被调用，session_id: {session_id}")

        try:
            # 确保Agent已初始化
            if not LogisticsService._initialized:
                await LogisticsService.initialize()

            # 提取用户输入文本
            user_input = LogisticsService._extract_user_text(content)
            logger.info(f"[LogisticsService] 用户输入: {user_input[:100]}...")

            # 构建用户消息
            user_msg = Msg(
                name="user",
                content=user_input,
                role="user"
            )

            # 获取会话历史（用于上下文理解）
            session_history = await session_manager.get_session_history(session_id)

            # ====================================================================
            # Step 1: 感知 - 提取关键信息
            # ====================================================================
            logger.info("[LogisticsService] === Step 1: 感知 ===")
            perception_msg = await LogisticsService._perceiver.perceive(user_msg)
            perception_result = perception_msg.metadata if hasattr(perception_msg, 'metadata') else {}
            logger.info(f"[LogisticsService] 感知结果: {perception_result}")

            # ====================================================================
            # Step 2: 推理 - 分析意图、规划步骤
            # ====================================================================
            logger.info("[LogisticsService] === Step 2: 推理 ===")
            reasoning_msg = await LogisticsService._reasoner.reason(
                user_input=user_input,
                perception_result=perception_result,
                conversation_history=session_history
            )
            reasoning_result = reasoning_msg.metadata if hasattr(reasoning_msg, 'metadata') else {}
            logger.info(f"[LogisticsService] 推理结果: intent={reasoning_result.get('intent')}")

            # ====================================================================
            # Step 3: 判断是否需要执行操作
            # ====================================================================
            execution_result: Optional[Dict[str, Any]] = None
            intent = reasoning_result.get("intent", "unknown")

            # 如果需要执行操作（query/modify/insert）
            if intent in ["query", "modify", "insert"]:
                logger.info("[LogisticsService] === Step 3: 执行 ===")

                # 构建执行指令
                action_msg = Msg(
                    name="Reasoner",
                    content=json.dumps({
                        "action": intent,
                        "order_number": reasoning_result.get("order_number"),
                        "target_status": reasoning_result.get("target_status"),
                        "new_info": reasoning_result.get("new_info", {}),
                    }, ensure_ascii=False),
                    role="assistant"
                )

                # 执行智能体执行操作
                exec_result_msg = await LogisticsService._actor(action_msg)
                execution_result = json.loads(exec_result_msg.content)
                logger.info(f"[LogisticsService] 执行结果: {execution_result}")

            # ====================================================================
            # Step 4: 对话 - 生成用户友好的回复
            # ====================================================================
            logger.info("[LogisticsService] === Step 4: 对话 ===")

            # 将推理结果转为字典（如果是对象则序列化）
            if isinstance(reasoning_result, dict):
                reasoning_dict = reasoning_result
            else:
                reasoning_dict = {
                    "intent": reasoning_result.get("intent") if hasattr(reasoning_result, "get") else "unknown",
                    "clarification_questions": reasoning_result.get("clarification_questions", []) if hasattr(reasoning_result, "get") else [],
                }

            response_msg = await LogisticsService._dialog.format_response(
                reasoning_result=reasoning_dict,
                execution_result=execution_result
            )

            # 提取回复文本（处理 content 可能是 list 或 str 的情况）
            reply_text = LogisticsService._extract_text_from_msg(response_msg)
            logger.info(f"[LogisticsService] 生成回复: {reply_text[:100]}...")

            # ====================================================================
            # Step 5: 保存会话历史
            # ====================================================================
            # 保存用户消息
            await session_manager.add_message(session_id, user_msg)

            # 保存助手回复
            assistant_msg = Msg(
                name="assistant",
                content=reply_text,
                role="assistant"
            )
            await session_manager.add_message(session_id, assistant_msg)

            # ====================================================================
            # 返回结果
            # ====================================================================
            return {
                'success': True,
                'message': reply_text,
                'data': {
                    'session_id': session_id,
                    'intent': intent,
                    'perception': perception_result,
                    'execution': execution_result,
                }
            }

        except Exception as e:
            logger.error(f"[LogisticsService] 处理失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'抱歉，处理您的请求时遇到了问题: {str(e)}',
                'data': {'error': str(e)}
            }

    @staticmethod
    async def clear_session(session_id: str, user_id: str = "default"):
        """
        清除指定会话的历史记录

        Args:
            session_id: 会话ID
            user_id: 用户ID
        """
        await session_manager.clear_session(session_id, user_id)
        logger.info(f"[LogisticsService] 会话已清除: {session_id}")

    @staticmethod
    async def get_session_history(session_id: str, user_id: str = "default"):
        """
        获取指定会话的历史记录

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            会话历史消息列表
        """
        return await session_manager.get_session_history(session_id, user_id)
