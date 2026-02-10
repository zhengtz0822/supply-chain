# agents/logistics_reasoning_agent.py
"""
推理智能体 - Reasoner

职责:
- 理解用户意图，分析对话上下文
- 决定需要执行的操作类型（查询/修改/插入）
- 规划任务执行步骤
- 协调多个子任务的执行顺序
"""
import logging
import json
from typing import Optional, Literal
from agentscope.agent import ReActAgent
from agentscope.message import Msg
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# 操作类型枚举
class ActionType(str):
    """支持的操作类型"""
    QUERY = "query"           # 查询物流状态
    MODIFY = "modify"         # 修改物流信息
    INSERT = "insert"         # 插入新的物流节点
    CLARIFY = "clarify"       # 需要向用户澄清信息
    UNKNOWN = "unknown"       # 无法识别意图


# 结构化输出模型 - 推理结果
class ReasoningResult(BaseModel):
    """推理智能体的结构化输出"""

    # 意图识别
    intent: Literal["query", "modify", "insert", "clarify", "unknown"] = Field(
        description="用户意图: query-查询, modify-修改, insert-插入, clarify-澄清, unknown-未知"
    )

    # 任务规划
    task_steps: list[str] = Field(
        default_factory=list,
        description="完成任务所需的步骤列表"
    )

    # 提取的参数
    order_number: Optional[str] = Field(
        default=None,
        description="订单号"
    )
    order_number: Optional[str] = Field(
        default=None,
        description="订单号"
    )

    # 修改/插入操作相关
    target_status: Optional[str] = Field(
        default=None,
        description="目标状态（修改操作）"
    )
    new_info: dict = Field(
        default_factory=dict,
        description="新增信息（插入操作），如 {location: 北京, time: 2024-01-01, plate: 京A12345}"
    )

    # 澄清相关
    clarification_questions: list[str] = Field(
        default_factory=list,
        description="需要向用户询问的问题列表"
    )

    # 置信度
    confidence: float = Field(
        default=0.0,
        description="推理置信度 0-1"
    )

    # 推理过程
    reasoning: str = Field(
        default="",
        description="推理过程的说明"
    )


class LogisticsReasoningAgent(ReActAgent):
    """
    物流推理智能体

    功能:
    1. 分析用户输入和感知结果，理解用户意图
    2. 根据意图决定操作类型
    3. 规划任务执行步骤
    4. 识别缺失信息，生成澄清问题
    """

    def __init__(self, model_config, formatter, **kwargs):
        super().__init__(
            name="Reasoner",
            sys_prompt="""你是一个物流业务推理专家，负责理解用户意图并规划执行步骤。

## 核心职责
1. **意图识别**: 分析用户想要做什么（查询/修改/插入）
2. **信息验证**: 检查是否具备执行所需的关键信息
3. **任务规划**: 将复杂任务分解为可执行的步骤
4. **问题生成**: 当信息不足时，生成需要向用户澄清的问题

## 支持的操作类型

### 1. QUERY (查询)
- 用户询问物流状态、运输进度
- 所需信息: order_number
- 示例: "查一下 order1234567890 的物流状态"

### 2. MODIFY (修改)
- 用户要求修改物流状态或信息
- 所需信息: order_number + 修改目标
- 示例: "把 order1234567890 的状态改为已送达"

### 3. INSERT (插入)
- 用户要求添加新的物流节点信息
- 所需信息: order_number + 新节点信息（位置、时间、车牌等）
- 示例: "给 order1234567890 添加一个新节点：北京转运中心，车牌京A12345"

### 4. CLARIFY (澄清)
- 信息不足，需要向用户询问
- 生成针对性的问题
- 示例问题: "请问订单号是多少？"

## 推理流程
1. 分析用户输入的意图和目标
2. 检查必需参数是否齐全
   - 查询: 必须有订单号
   - 修改: 必须有订单号和修改目标
   - 插入: 必须有订单号和新增信息
3. 如果信息不足，返回 CLARIFY 并生成问题
4. 如果信息充足，规划执行步骤
5. 返回结构化的推理结果

## 输出格式
返回 JSON 格式，包含:
- intent: 操作类型 (query/modify/insert/clarify/unknown)
- task_steps: 执行步骤列表
- order_number: 订单号
- target_status: 目标状态（修改操作）
- new_info: 新增信息字典（插入操作）
- clarification_questions: 澄清问题列表
- confidence: 置信度 (0-1)
- reasoning: 推理过程说明

## 注意事项
- 用户可能使用模糊表达，需要根据上下文推断
- 订单号是本系统的核心标识，务必准确识别
- 修改操作需要确认用户权限（预留）
- 插入操作需要验证信息的完整性
- 不确定时优先选择 CLARIFY，避免错误操作
""",
            model=model_config,
            formatter=formatter,
            **kwargs
        )
        logger.info("[Reasoner] 物流推理智能体已初始化")

    async def reason(
        self,
        user_input: str,
        perception_result: Optional[dict] = None,
        conversation_history: Optional[list] = None
    ) -> Msg:
        """
        推理用户意图，规划执行步骤

        Args:
            user_input: 用户原始输入
            perception_result: 感知智能体的提取结果
            conversation_history: 对话历史（用于上下文理解）

        Returns:
            包含推理结果的消息，结构化输出为 ReasoningResult
        """
        logger.info(f"[Reasoner] 开始推理分析，用户输入: {user_input[:50]}...")

        # 构建推理输入
        reasoning_input = self._build_reasoning_input(
            user_input, perception_result, conversation_history
        )

        # 创建推理消息
        reasoning_msg = Msg(
            name="user",
            content=reasoning_input,
            role="user"
        )

        try:
            # 调用模型进行推理，使用结构化输出
            result_msg: Msg = await self(
                reasoning_msg,
                structured_model=ReasoningResult,
            )

            # 提取结构化数据
            reasoning_data = result_msg.metadata

            logger.info(
                f"[Reasoner] 推理完成，"
                f"意图: {reasoning_data.get('intent')}, "
                f"置信度: {reasoning_data.get('confidence', 0)}"
            )

            return result_msg

        except Exception as e:
            logger.error(f"[Reasoner] 推理失败: {e}", exc_info=True)
            # 返回一个错误结果
            return Msg(
                name=self.name,
                role="assistant",
                content=json.dumps({
                    "error": str(e),
                    "intent": "unknown",
                    "confidence": 0.0,
                    "reasoning": "推理过程发生错误"
                }, ensure_ascii=False)
            )

    def _build_reasoning_input(
        self,
        user_input: str,
        perception_result: Optional[dict],
        conversation_history: Optional[list]
    ) -> str:
        """
        构建推理输入

        Args:
            user_input: 用户输入
            perception_result: 感知结果
            conversation_history: 对话历史

        Returns:
            格式化的推理输入字符串
        """
        parts = []

        # 感知结果
        if perception_result:
            parts.append("## 感知智能体提取的信息:")
            parts.append(f"```json")
            parts.append(json.dumps(perception_result, ensure_ascii=False, indent=2))
            parts.append(f"```")

        # 对话历史摘要
        if conversation_history and len(conversation_history) > 0:
            parts.append("\n## 对话上下文:")
            recent = conversation_history[-3:]  # 最近3条
            for msg in recent:
                parts.append(f"- {msg.name}: {msg.content}")

        # 用户输入
        parts.append(f"\n## 用户当前输入:")
        parts.append(user_input)

        parts.append("\n请根据以上信息进行推理，确定用户意图和执行计划。")

        return "\n".join(parts)

    def extract_intent_from_text(self, text: str) -> str:
        """
        从文本中快速推断意图（辅助方法，作为 fallback）

        Args:
            text: 输入文本

        Returns:
            推断的意图类型
        """
        text_lower = text.lower()

        # 查询关键词
        query_keywords = ["查", "查询", "看", "看看", "在哪里", "到哪", "状态", "进度"]
        # 修改关键词
        modify_keywords = ["修改", "改", "更改", "更新", "设为"]
        # 插入关键词
        insert_keywords = ["添加", "插入", "新增", "加上", "补录"]

        for keyword in query_keywords:
            if keyword in text_lower:
                return "query"

        for keyword in modify_keywords:
            if keyword in text_lower:
                return "modify"

        for keyword in insert_keywords:
            if keyword in text_lower:
                return "insert"

        return "unknown"
