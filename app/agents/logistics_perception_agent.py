# agents/logistics_perception_agent.py
"""
感知智能体 - Perceiver

职责:
- 识别用户输入中的图片内容（物流面单、快递单等）
- 提取关键信息: 物流单号、订单号、地址、联系方式等
- 将非结构化内容（图片/语音/自由文本）转换为结构化数据
"""
import logging
import json
from typing import Optional
from agentscope.agent import ReActAgent
from agentscope.message import Msg
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# 结构化输出模型 - 感知结果
class PerceptionResult(BaseModel):
    """感知智能体的结构化输出"""

    # 提取的实体信息
    order_number: Optional[str] = Field(
        default=None,
        description="订单号，如 order1234567890、ORD-2024-001"
    )
    phone: Optional[str] = Field(
        default=None,
        description="电话号码"
    )
    address: Optional[str] = Field(
        default=None,
        description="地址信息"
    )
    company: Optional[str] = Field(
        default=None,
        description="物流公司，如 顺丰、京东、圆通等"
    )

    # 图片分析结果
    image_description: Optional[str] = Field(
        default=None,
        description="图片内容描述"
    )
    confidence: float = Field(
        default=0.0,
        description="识别置信度 0-1"
    )

    # 状态信息
    current_status: Optional[str] = Field(
        default=None,
        description="从图片/文本中识别的当前物流状态"
    )


class LogisticsPerceptionAgent(ReActAgent):
    """
    物流感知智能体

    功能:
    1. 识别图片中的物流单号、二维码、条形码
    2. 提取面单上的关键信息（收发件人、地址、时间等）
    3. 理解自然语言中的物流信息描述
    """

    def __init__(self, model_config, formatter, **kwargs):
        super().__init__(
            name="Perceiver",
            sys_prompt="""你是一个物流信息感知专家，专门从用户的输入中提取物流相关关键信息。

## 核心能力
1. **图片识别**: 识别物流面单、快递单、截图中的关键信息
2. **信息提取**: 提取订单号、地址、电话、物流公司等
3. **状态识别**: 从面单或描述中识别当前物流状态

## 订单号特征识别
- 本系统订单号: 通常以 "order" 开头，后跟数字 (如 order1234567890)
- 订单号格式: ORD-开头 + 年份 + 数字 (如 ORD-2024-001)
- 纯数字格式: 10-20位纯数字 (如 12345678901234567890)

## 输出格式
你必须以 JSON 格式返回结果，包含以下字段:
- order_number: 订单号
- phone: 电话号码
- address: 地址
- company: 物流公司名称
- image_description: 图片内容描述
- confidence: 识别置信度 (0-1)
- current_status: 当前状态

## 工作流程
1. 首先分析输入内容（文本/图片）
2. 识别是否包含物流相关信息
3. 提取所有可见的关键信息，特别注意订单号
4. 评估识别结果的置信度
5. 返回结构化 JSON 结果

## 注意事项
- 订单号是本系统的核心标识，务必准确提取
- 如果信息不完整或模糊，置信度应设置较低（< 0.5）
- 图片质量差时，应在 image_description 中说明
- 找不到某项信息时，该字段设为 null
- 始终保持客观，不确定的信息不要编造
""",
            model=model_config,
            formatter=formatter,
            **kwargs
        )
        logger.info("[Perceiver] 物流感知智能体已初始化")

    async def perceive(self, msg: Msg) -> Msg:
        """
        感知用户输入，提取关键信息

        Args:
            msg: 用户消息（可能包含文本、图片等）

        Returns:
            包含感知结果的消息，结构化输出为 PerceptionResult
        """
        logger.info(f"[Perceiver] 开始感知分析，来源: {msg.name}")

        # 检查消息内容是否包含图片
        # content = msg.content
        # has_image = False
        #
        # if isinstance(content, list):
        #     # 多模态内容，检查是否有图片
        #     for item in content:
        #         if isinstance(item, dict):
        #             if item.get("type") == "image":
        #                 has_image = True
        #                 break
        #         elif hasattr(item, "type"):
        #             if item.type == "image":
        #                 has_image = True
        #                 break
        # elif isinstance(content, str):
        #     # 纯文本内容，没有图片
        #     has_image = False
        #
        # # 如果没有图片，直接返回默认结果（避免 formatter 报错）
        # if not has_image:
        #     logger.info("[Perceiver] 未检测到图片，返回默认感知结果")
        #     result = PerceptionResult(
        #         order_number=None,
        #         phone=None,
        #         address=None,
        #         company=None,
        #         image_description="未提供图片，无法进行图片识别",
        #         confidence=0.0,
        #         current_status=None
        #     )
        #     return Msg(
        #         name=self.name,
        #         role="assistant",
        #         content=result.model_dump_json(),
        #         metadata=result.model_dump()
        #     )

        # 调用父类的 reply 方法，使用结构化输出
        try:
            result_msg: Msg = await self(
                msg,
                structured_model=PerceptionResult,
            )

            # 提取结构化数据
            perception_data = result_msg.metadata

            # 安全地获取感知数据，避免 None 错误
            order_number = perception_data.get('order_number') if perception_data else None
            confidence = perception_data.get('confidence', 0) if perception_data else 0
            
            logger.info(
                f"[Perceiver] 感知完成，"
                f"订单号: {order_number}, "
                f"置信度: {confidence}"
            )

            return result_msg

        except Exception as e:
            logger.error(f"[Perceiver] 感知失败: {e}", exc_info=True)
            # 返回一个错误结果
            return Msg(
                name=self.name,
                role="assistant",
                content=json.dumps({
                    "error": str(e),
                    "order_number": None,
                    "confidence": 0.0
                }, ensure_ascii=False)
            )

    def extract_order_number(self, text: str) -> Optional[str]:
        """
        从文本中提取订单号（辅助方法）

        Args:
            text: 输入文本

        Returns:
            提取到的订单号或 None
        """
        import re

        # 订单号正则模式
        patterns = [
            r'\border[a-zA-Z0-9]{8,20}\b',      # order 开头 (如 order123456)
            r'\bORD[-_]?\d{4}[-_]?\d{3,}\b',   # ORD-2024-001 格式
            r'\b\d{10,25}\b',                   # 纯数字 10-25 位
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        return None
