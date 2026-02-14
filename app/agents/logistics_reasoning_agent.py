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


# 运输状态枚举
class TransportStatus(str):
    """运输状态枚举"""
    PENDING_PICKUP = "待提货"
    IN_TRANSIT = "运输中"
    DELIVERED = "已送达"
    RECEIPT_CONFIRMED = "已回单"
    DELAYED = "异常滞留"


# 修改子类型枚举
class ModifyType(str):
    """修改操作子类型"""
    MODIFY_STATUS = "modify_status"     # 修改运输状态
    MODIFY_NODE = "modify_node"         # 修改物流节点信息


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
    order_id: Optional[str] = Field(
        default=None,
        description="订单ID（数据库唯一标识）"
    )
    order_number: Optional[str] = Field(
        default=None,
        description="订单编号（业务编号）"
    )

    # 修改操作相关 - 修改类型
    modify_type: Optional[Literal["modify_status", "modify_node"]] = Field(
        default=None,
        description="修改子类型: modify_status-修改运输状态, modify_node-修改物流节点信息"
    )

    # 修改操作相关 - 修改运输状态
    transport_status_name: Optional[Literal["待提货", "运输中", "已送达", "已回单", "异常滞留"]] = Field(
        default=None,
        description="运输状态（修改运输状态操作），可选值: 待提货、运输中、已送达、已回单、异常滞留"
    )

    # 修改操作相关 - 修改物流节点
    order_id: Optional[str] = Field(
        default=None,
        description="订单ID（修改物流节点操作，从查询结果中获取）"
    )
    tracking_id: Optional[str] = Field(
        default=None,
        description="物流轨迹ID（修改物流节点操作，从查询结果中获取）"
    )
    node_location: Optional[str] = Field(
        default=None,
        description="发生地点（修改物流节点操作，必要参数）"
    )
    status_description: Optional[str] = Field(
        default=None,
        description="状态描述（修改物流节点操作，可选参数）"
    )
    operator: Optional[str] = Field(
        default=None,
        description="操作人（修改物流节点操作，可选参数）"
    )
    vehicle_plate: Optional[str] = Field(
        default=None,
        description="车牌号（修改物流节点操作，可选参数）"
    )
    occurred_at_str: Optional[str] = Field(
        default=None,
        description="发生时间（修改物流节点操作，可选参数，格式: yyyy-MM-dd）"
    )
    remark: Optional[str] = Field(
        default=None,
        description="备注（修改物流节点操作，可选参数）"
    )
    content: Optional[str] = Field(
        default=None,
        description="物流信息（修改/插入物流节点操作，可选参数），用于表示如'货物已送达收货地点'、'货物已从中转站发出'等自定义信息"
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
- 所需信息: order_number 或 order_id
- 示例: "查一下 order1234567890 的物流状态"

### 2. MODIFY (修改)
修改操作分为两种子类型:

#### 2.1 MODIFY_STATUS (修改运输状态)
- 用户要求修改订单的运输状态
- 所需信息:
  - order_number（订单编号）或 order_id（订单ID）
  - transport_status_name（目标运输状态）
- 支持的运输状态:
  1. 待提货
  2. 运输中
  3. 已送达
  4. 已回单
  5. 异常滞留
- 示例:
  - "把 order1234567890 的状态改为已送达"
  - "订单 ORD-2024-001 改为运输中"

#### 2.2 MODIFY_NODE (修改物流节点信息)
- 用户要求修改已有物流节点（轨迹）的信息
- 所需信息:
  - order_id（订单ID，从之前的查询结果中获取）
  - tracking_id（物流轨迹ID，从之前的查询结果中获取，用户通常不会直接提供，需要从上下文推断）
  - 至少一个要修改的字段（node_location/status_description/operator/vehicle_plate/occurred_at_str/remark）
- 可修改字段:
  - node_location（发生地点）
  - status_description（状态描述）
  - operator（操作人）
  - vehicle_plate（车牌号）
  - occurred_at_str（发生时间，格式: yyyy-MM-dd）
  - remark（备注）
  - content（物流信息，如"货物已送达收货地点"、"货物已从中转站发出"等自定义信息）
- 示例:
  - "把深圳南山区那个节点的备注改成客户不在" → 只返回 remark，其他字段为 null
  - "修改一下深圳节点的车牌号为粤B12345" → 只返回 vehicle_plate
  - "把到达节点的时间改为2024-01-15" → 只返回 occurred_at_str
  - "把北京节点的物流信息改成货物已送达收货地点" → 只返回 content
- **重要**: 只返回用户明确要修改的字段，未提及的字段必须为 null，不要填充
- 注意: order_id 和 tracking_id 需要从对话上下文中的查询结果获取
- 注意: session_id 由框架自动处理，无需关注

### 3. INSERT (插入物流节点)
- 用户要求添加新的物流节点信息
- 所需信息（必填）:
  - order_id（订单唯一ID）
  - status_description（物流状态描述）
  - node_location（发生地点）
  - occurred_at_str（发生时间，格式: yyyy-MM-dd）
- 可选参数:
  - operator（操作人）
  - vehicle_plate（车牌号）
  - remark（备注）
  - content（物流信息，如"货物已送达收货地点"、"货物已从中转站发出"等自定义信息）
- 示例:
  - "给订单添加一个新节点：已到达北京转运中心，时间2024-01-15"
  - "添加物流节点：深圳，已装车，车牌粤B12345"
  - "添加一个节点：上海中转站，货物已从中转站发出"
- 注意: order_id 是订单的唯一标识，用于确定要插入节点的订单

### 4. CLARIFY (澄清)
- 信息不足，需要向用户询问
- 生成针对性的问题
- 示例问题: "请问订单号是多少？", "请确认要修改为什么状态？（待提货/运输中/已送达/已回单/异常滞留）"

## 推理流程
1. 分析用户输入的意图和目标
2. 检查必需参数是否齐全
   - 查询: 必须有 order_number 或 order_id
   - 修改运输状态: 必须有订单标识和 transport_status_name，设置 modify_type="modify_status"
   - 修改物流节点: 必须有 order_id（从上下文获取）、tracking_id（从上下文推断）和 location，设置 modify_type="modify_node"
   - 插入物流节点: 必须有 order_id、status_description、node_location 和 occurred_at_str
3. 如果信息不足，返回 CLARIFY 并生成问题
4. 如果信息充足，规划执行步骤
5. 返回结构化的推理结果

## 输出格式
返回 JSON 格式，包含:
- intent: 操作类型 (query/modify/insert/clarify/unknown)
- modify_type: 修改子类型 (modify_status/modify_node，仅当 intent=modify 时)
- task_steps: 执行步骤列表
- order_id: 订单ID（可选）
- order_number: 订单编号（可选）

# 修改运输状态时:
- transport_status_name: 运输状态（必须为5个选项之一）

# 修改物流节点时:
- order_id: 订单ID（从查询结果获取）
- tracking_id: 物流轨迹ID（从查询结果获取）
- node_location: 发生地点（必要参数）
- status_description: 状态描述（可选）
- operator: 操作人（可选）
- vehicle_plate: 车牌号（可选）
- occurred_at_str: 发生时间（可选，格式: yyyy-MM-dd）
- remark: 备注（可选）
- content: 物流信息（可选，如"货物已送达收货地点"等自定义信息）

# 插入物流节点时:
- order_id: 订单唯一ID（必填）
- status_description: 物流状态描述（必填）
- node_location: 发生地点（必填）
- occurred_at_str: 发生时间（必填，格式: yyyy-MM-dd）
- operator: 操作人（可选）
- vehicle_plate: 车牌号（可选）
- remark: 备注（可选）
- content: 物流信息（可选，如"货物已从中转站发出"等自定义信息）

- clarification_questions: 澄清问题列表
- confidence: 置信度 (0-1)
- reasoning: 推理过程说明

## 注意事项
- 用户可能使用模糊表达，需要根据上下文推断
- 订单号是本系统的核心标识，务必准确识别
- 修改物流节点时，tracking_id 需要从对话上下文的查询结果中匹配（根据地点、时间等信息）
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
        perception_result: Optional[dict] = None
    ) -> Msg:
        """
        推理用户意图，规划执行步骤

        Args:
            user_input: 用户原始输入
            perception_result: 感知智能体的提取结果

        Returns:
            包含推理结果的消息，结构化输出为 ReasoningResult
        """
        logger.info(f"[Reasoner] 开始推理分析，用户输入: {user_input[:50]}...")

        # 构建推理输入（使用 self.memory 获取对话历史）
        reasoning_input = await self._build_reasoning_input(
            user_input, perception_result
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

    async def _build_reasoning_input(
        self,
        user_input: str,
        perception_result: Optional[dict]
    ) -> str:
        """
        构建推理输入

        Args:
            user_input: 用户输入
            perception_result: 感知结果

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

        # 对话历史摘要（从 self.memory 获取）
        if self.memory is not None:
            conversation_history = await self.memory.get_memory()
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
