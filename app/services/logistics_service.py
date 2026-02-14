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
import asyncio
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import create_async_engine
from agentscope.message import Msg, ImageBlock, Base64Source, TextBlock
from app.core.config import get_settings
from agentscope.pipeline import MsgHub
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.formatter import DashScopeMultiAgentFormatter
from agentscope.memory import AsyncSQLAlchemyMemory, InMemoryMemory

from app.agents.logistics_perception_agent import LogisticsPerceptionAgent
from app.agents.logistics_reasoning_agent import LogisticsReasoningAgent
from app.agents.logistics_action_agent import LogisticsActionAgent
from app.agents.logistics_dialog_agent import LogisticsDialogAgent
from agentscope.message import (
    Msg,
    Base64Source,
    URLSource,
    TextBlock,
    ThinkingBlock,
    ImageBlock,
    AudioBlock,
    VideoBlock,
    ToolUseBlock,
    ToolResultBlock,
)
logger = logging.getLogger(__name__)


class LogisticsService:
    """
    物流跟踪服务

    职责:
    1. 初始化共享资源（模型配置、数据库引擎）
    2. 为每个请求创建独立的Agent实例（方案A：保证并发安全）
    3. 协调多Agent工作流程
    4. 通过Memory实现会话上下文持久化
    """

    # 类变量，存储共享配置（不存储Agent实例）
    _model_config = None
    _vision_model_config = None
    _single_formatter = None
    _multi_formatter = None
    _memory_engine = None
    _initialized = False

    @classmethod
    async def initialize(cls):
        """
        初始化共享资源（模型配置、数据库引擎）

        应在应用启动时调用一次
        注意：不创建Agent实例，Agent在每次请求时创建（方案A）
        """
        if cls._initialized:
            return

        logger.info("[LogisticsService] 开始初始化共享资源...")

        # 获取模型配置
        import agentscope
        api_key = get_settings().DASHSCOPE_API_KEY
        # 初始化 AgentScope
        agentscope.init()

        # 创建数据库引擎（共享，用于创建Memory实例）
        cls._memory_engine = create_async_engine(
            "sqlite+aiosqlite:///./supply_chain_memory.db",
            echo=False
        )
        logger.info("[LogisticsService] 数据库引擎已创建")

        # 创建模型配置（共享）
        cls._model_config = DashScopeChatModel(
            model_name="qwen-plus",
            api_key=api_key,
            stream=False,
        )

        # 创建感知模型配置（视觉模型）
        cls._vision_model_config = DashScopeChatModel(
            model_name="qwen-vl-plus",
            api_key=api_key,
            stream=False,
        )

        # 创建格式化器（共享）
        cls._single_formatter = DashScopeChatFormatter()
        cls._multi_formatter = DashScopeMultiAgentFormatter()

        cls._initialized = True
        logger.info("[LogisticsService] 共享资源初始化完成（方案A：每请求创建新Agent）")

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
    def _build_user_message(content: List) -> Any:
        """
        构建多模态用户消息（支持文本+图片）

        按照 DashScope formatter 期望的格式：
        - 文本: {"type": "text", "text": "..."}
        - 图片: {"type": "image", "source": {"type": "base64", "data": "..."}}

        Args:
            content: 用户输入的内容列表

        Returns:
            多模态内容对象（文本或列表）
        """
        # 分离文本和图片
        content_blocks = []

        for item in content:
            if item.get("type") == "text":
                content_blocks.append(TextBlock(type="text",text=item.get("text", "")))
            elif item.get("type") == "image_url":
                content_blocks.append(
                    ImageBlock(
                        type="image",
                        source=URLSource(
                            type="url",
                            url=item.get("image_url", "")
                        )
                    )
                )
            elif item.get("type") == "image":
                content_blocks.append(
                    ImageBlock(
                    type="image",
                    source=Base64Source(
                        type="base64",
                        media_type=f"image/{item.get('extension', 'png')}",
                        data=item.get("image", "")
                    )
                ))
            elif item.get("type") == "audio":
                content_blocks.append(AudioBlock(
                    source=Base64Source(
                        type="base64",
                        media_type="audio/mpeg",
                        data=item.get("audio", "")
                    )
                ))
            elif item.get("type") == "video":
                content_blocks.append(VideoBlock(
                    source=Base64Source(
                        type="base64",
                        media_type="video/mp4",
                        data=item.get("video", "")
                    )
                ))

        return content_blocks

        # # 如果没有图片，只返回文本
        # if not images:
        #     return " ".join(texts)
        #
        # # 有图片时，构建多模态内容
        # result = []
        #
        # # 添加文本块（使用 TextBlock 类）
        # if texts:
        #     result.append(TextBlock(text=" ".join(texts)))
        #
        # # 添加图片块（使用 ImageBlock 和 Base64Source 类）
        # for base64_data in images:
        #     image_block = ImageBlock(
        #         source=Base64Source(
        #             type="base64",
        #             media_type="image/jpeg",  # 关键：使用 media_type 而不是 type
        #             data=base64_data
        #         )
        #     )
        #     result.append(image_block)

        return result

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
    def _create_agents(memory=None):
        """
        创建新的Agent实例（工厂方法）

        每次请求调用此方法创建独立的Agent实例，保证并发安全

        Args:
            memory: 会话记忆对象（可选，用于多轮对话）

        Returns:
            (perceiver, reasoner, actor, dialog) 四个Agent实例的元组
        """
        perceiver = LogisticsPerceptionAgent(
            model_config=LogisticsService._vision_model_config,
            formatter=LogisticsService._multi_formatter,
            memory=memory,
        )

        reasoner = LogisticsReasoningAgent(
            model_config=LogisticsService._model_config,
            formatter=LogisticsService._multi_formatter,
            memory=memory,
        )

        actor = LogisticsActionAgent()

        dialog = LogisticsDialogAgent(
            model_config=LogisticsService._model_config,
            formatter=LogisticsService._single_formatter,
            memory=memory,
        )

        return perceiver, reasoner, actor, dialog

    @staticmethod
    async def chat(session_id: str, content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        物流订单对话处理入口


        工作流程:
        1. 为本次请求创建独立的 Memory（实现会话隔离）
        2. 感知智能体提取关键信息（单号、地址等）
        3. 推理智能体分析意图、规划步骤
        4. 执行智能体执行业务操作
        5. 对话智能体生成用户友好的回复

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

        # 确保共享资源已初始化
        if not LogisticsService._initialized:
            await LogisticsService.initialize()
        import agentscope
        # 初始化agentScope
        agentscope.init(studio_url="http://localhost:3000")

        # 先创建会话独立的 Memory
        # 注意：如果之前的测试导致 memory 中有格式不兼容的历史消息，
        # 可能导致 formatter 报错。清除旧会话可以解决此问题。
        memory = AsyncSQLAlchemyMemory(
            engine_or_session=LogisticsService._memory_engine,
            user_id="default",
            session_id=session_id,
        )
        logger.info(f"[LogisticsService] 创建会话独立 Memory: {session_id}")

        # 创建本次请求专用的 Agent 实例（方案A：并发安全），并传入 Memory
        perceiver, reasoner, actor, dialog = LogisticsService._create_agents(memory=memory)
        logger.info(f"[LogisticsService] 创建新Agent实例（方案A）")

        try:
            # 构建多模态用户消息（支持图片）
            user_content = LogisticsService._build_user_message(content)
            logger.info(f"[LogisticsService] 用户输入内容类型: {type(user_content).__name__}")

            # 遍历user_content,如果元素中的有

            # 构建用户消息
            user_msg = Msg(
                name="user",
                content=user_content,  # 可能是字符串或列表（多模态）
                role="user"
            )

            # 暂不添加多模态内容到 memory（序列化可能有问题）
            # await memory.add(user_msg)

            # ====================================================================
            # Step 1: 感知 - 提取关键信息
            # ====================================================================
            logger.info("[LogisticsService] === Step 1: 感知 ===")
            perception_msg = await perceiver.perceive(user_msg)
            perception_result = perception_msg.metadata if hasattr(perception_msg, 'metadata') else {}
            logger.info(f"[LogisticsService] 感知结果: {perception_result}")

            # ====================================================================
            # Step 2: 推理 - 分析意图、规划步骤
            # ====================================================================
            logger.info("[LogisticsService] === Step 2: 推理 ===")

            # 提取纯文本用于推理（Reasoner 不需要图片）
            user_input = LogisticsService._extract_user_text(content)
            reasoning_msg = await reasoner.reason(
                user_input=user_input,
                perception_result=perception_result
            )
            reasoning_result = reasoning_msg.metadata if hasattr(reasoning_msg, 'metadata') else {}
            logger.info(f"[LogisticsService] 推理结果: intent={reasoning_result.get('intent')}")

            # ====================================================================
            # Step 3: 判断是否需要执行操作
            # ====================================================================
            execution_result: Optional[Dict[str, Any]] = None
            intent = reasoning_result.get("intent", "unknown")

            # 如果需要执行操作（query/modify/modify_node/insert）
            if intent in ["query", "modify", "modify_node", "insert"]:
                logger.info("[LogisticsService] === Step 3: 执行 ===")

                # 判断是否为修改物流节点操作
                modify_type = reasoning_result.get("modify_type")

                if modify_type == "modify_node":
                    # 修改物流节点信息
                    action = "modify_node"
                    action_content = {
                        "action": action,
                        "session_id": session_id,
                        "order_id": reasoning_result.get("order_id"),
                        "tracking_id": reasoning_result.get("tracking_id"),
                        "node_location": reasoning_result.get("node_location"),
                        "status_description": reasoning_result.get("status_description"),
                        "operator": reasoning_result.get("operator"),
                        "vehicle_plate": reasoning_result.get("vehicle_plate"),
                        "occurred_at_str": reasoning_result.get("occurred_at_str"),
                        "remark": reasoning_result.get("remark"),
                        "content": reasoning_result.get("content"),
                    }
                elif intent == "insert":
                    # 插入物流节点信息
                    action = "insert"
                    action_content = {
                        "action": action,
                        "session_id": session_id,
                        "order_id": reasoning_result.get("order_id"),
                        "node_location": reasoning_result.get("node_location"),
                        "occurred_at_str": reasoning_result.get("occurred_at_str"),
                        "status_description": reasoning_result.get("status_description"),
                        "operator": reasoning_result.get("operator"),
                        "vehicle_plate": reasoning_result.get("vehicle_plate"),
                        "remark": reasoning_result.get("remark"),
                        "content": reasoning_result.get("content"),
                    }
                else:
                    # 其他操作类型（query/modify）
                    action = intent
                    action_content = {
                        "action": intent,
                        "session_id": session_id,  # 添加会话ID用于审计追踪
                        "order_id": reasoning_result.get("order_id"),
                        "order_number": reasoning_result.get("order_number"),
                        "transport_status_name": reasoning_result.get("transport_status_name"),
                        "new_info": reasoning_result.get("new_info", {}),
                    }

                # 构建执行指令
                action_msg = Msg(
                    name="Reasoner",
                    content=json.dumps(action_content, ensure_ascii=False),
                    role="assistant"
                )

                # 执行智能体执行操作
                exec_result_msg = await actor(action_msg)
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

            response_msg = await dialog.format_response(
                reasoning_result=reasoning_dict,
                execution_result=execution_result
            )

            # 提取回复文本（处理 content 可能是 list 或 str 的情况）
            reply_text = LogisticsService._extract_text_from_msg(response_msg)
            logger.info(f"[LogisticsService] 生成回复: {reply_text[:100]}...")

            # 将助手回复添加到 memory
            assistant_msg = Msg(
                name="assistant",
                content=reply_text,
                role="assistant"
            )
            await memory.add(assistant_msg)

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
        memory = AsyncSQLAlchemyMemory(
            engine_or_session=LogisticsService._memory_engine,
            user_id=user_id,
            session_id=session_id,
        )
        await memory.drop()
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
        memory = AsyncSQLAlchemyMemory(
            engine_or_session=LogisticsService._memory_engine,
            user_id=user_id,
            session_id=session_id,
        )
        return await memory.get_memory()
