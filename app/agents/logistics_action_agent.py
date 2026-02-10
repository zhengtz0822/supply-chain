# agents/logistics_action_agent.py
"""
执行智能体 - Actor

职责:
- 执行具体的业务操作（查询/修改/插入）
- 调用业务系统 API
- 处理执行结果和异常
- 返回操作结果
"""
import logging
import json
from typing import Optional, Dict, Any
from agentscope.agent import AgentBase
from agentscope.message import Msg

logger = logging.getLogger(__name__)


class LogisticsActionAgent(AgentBase):
    """
    物流执行智能体

    功能:
    1. 执行查询物流状态的操作
    2. 执行修改物流信息的操作
    3. 执行插入物流节点的操作
    4. 处理业务 API 调用和结果返回
    """

    # ========================================================================
    # 业务 API 调用方法（伪代码，待接入真实 API）
    # ========================================================================

    async def _api_query_logistics(self, order_number: str) -> Dict[str, Any]:
        """
        查询物流状态（伪代码）

        Args:
            order_number: 订单号

        Returns:
            物流信息字典
        """
        # TODO: 接入真实业务 API
        # 示例伪代码:
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         f"{API_BASE_URL}/logistics/{order_number}"
        #     )
        #     return response.json()

        # 模拟返回数据
        logger.info(f"[Actor] 调用查询API: {order_number}")
        return {
            "order_number": order_number,
            "status": "在途中",
            "current_location": "北京转运中心",
            "estimated_delivery": "2024-01-15",
            "history": [
                {"time": "2024-01-10 10:00", "location": "深圳", "status": "已揽收"},
                {"time": "2024-01-12 08:00", "location": "武汉", "status": "运输中"},
                {"time": "2024-01-13 15:00", "location": "北京", "status": "到达"},
            ]
        }

    async def _api_modify_logistics(
        self,
        order_number: str,
        target_status: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        修改物流信息（伪代码）

        Args:
            order_number: 订单号
            target_status: 目标状态
            **kwargs: 其他修改参数

        Returns:
            操作结果
        """
        # TODO: 接入真实业务 API
        # 示例伪代码:
        # async with httpx.AsyncClient() as client:
        #     response = await client.put(
        #         f"{API_BASE_URL}/logistics/{order_number}",
        #         json={"status": target_status, **kwargs}
        #     )
        #     return response.json()

        # 模拟返回数据
        logger.info(f"[Actor] 调用修改API: {order_number} -> {target_status}")
        return {
            "success": True,
            "order_number": order_number,
            "message": f"物流状态已更新为: {target_status}",
            "updated_at": "2024-01-13 16:00"
        }

    async def _api_insert_logistics_node(
        self,
        order_number: str,
        location: str,
        time: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        插入物流节点（伪代码）

        Args:
            order_number: 订单号
            location: 位置
            time: 时间
            **kwargs: 其他参数（如车牌号、操作人等）

        Returns:
            操作结果
        """
        # TODO: 接入真实业务 API
        # 示例伪代码:
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{API_BASE_URL}/logistics/{order_number}/nodes",
        #         json={
        #             "location": location,
        #             "time": time,
        #             **kwargs
        #         }
        #     )
        #     return response.json()

        # 模拟返回数据
        plate = kwargs.get("plate", "未知")
        logger.info(f"[Actor] 调用插入节点API: {order_number}, {location}, {plate}")
        return {
            "success": True,
            "order_number": order_number,
            "node_id": "NODE_" + str(hash(location + time)),
            "message": f"已插入新节点: {location} (车牌: {plate})",
            "inserted_at": "2024-01-13 16:00"
        }

    # ========================================================================
    # Agent 接口方法
    # ========================================================================

    def __init__(self):
        """初始化执行智能体"""
        super().__init__()
        logger.info("[Actor] 物流执行智能体已初始化")

    async def reply(self, x: Msg) -> Msg:
        """
        执行操作

        Args:
            x: 包含执行指令的消息
               content 格式:
               {
                   "action": "query" | "modify" | "insert",
                   "tracking_number": "...",
                   "target_status": "...",  # 修改操作
                   "new_info": {...}        # 插入操作
               }

        Returns:
            执行结果消息
        """
        logger.info(f"[Actor] 收到执行指令: {x.name}")

        try:
            # 解析指令
            if isinstance(x.content, str):
                data = json.loads(x.content)
            else:
                data = x.content

            action = data.get("action")
            order_number = data.get("order_number")

            # 根据操作类型执行
            if action == "query":
                result = await self._execute_query(order_number, data)

            elif action == "modify":
                result = await self._execute_modify(order_number, data)

            elif action == "insert":
                result = await self._execute_insert(order_number, data)

            else:
                result = {
                    "success": False,
                    "error": f"未知操作类型: {action}"
                }

            logger.info(f"[Actor] 执行完成: {action}, success: {result.get('success', True)}")

            return Msg(
                name="Actor",
                content=json.dumps(result, ensure_ascii=False),
                role="assistant"
            )

        except json.JSONDecodeError as e:
            logger.error(f"[Actor] JSON 解析失败: {e}")
            return Msg(
                 name="Actor",
                content=json.dumps({
                    "success": False,
                    "error": f"指令格式错误: {e}"
                }, ensure_ascii=False),
                role="assistant"
            )

        except Exception as e:
            logger.error(f"[Actor] 执行失败: {e}", exc_info=True)
            return Msg(
                name="Actor",
                content=json.dumps({
                    "success": False,
                    "error": str(e)
                }, ensure_ascii=False),
                role="assistant"
            )

    # ========================================================================
    # 具体操作实现
    # ========================================================================

    async def _execute_query(
        self,
        order_number: Optional[str],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行查询操作

        Args:
            order_number: 订单号
            data: 完整指令数据

        Returns:
            查询结果
        """
        if not order_number:
            return {
                "success": False,
                "error": "缺少订单号"
            }

        # 调用查询 API
        logistics_info = await self._api_query_logistics(order_number)

        return {
            "action": "query",
            "success": True,
            "data": logistics_info
        }

    async def _execute_modify(
        self,
        order_number: Optional[str],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行修改操作

        Args:
            order_number: 订单号
            data: 完整指令数据

        Returns:
            修改结果
        """
        if not order_number:
            return {
                "success": False,
                "error": "缺少订单号"
            }

        target_status = data.get("target_status")
        if not target_status:
            return {
                "success": False,
                "error": "缺少目标状态"
            }

        # 调用修改 API
        result = await self._api_modify_logistics(
            order_number=order_number,
            target_status=target_status,
            **{k: v for k, v in data.items() if k not in ["action", "order_number", "target_status"]}
        )

        return {
            "action": "modify",
            "success": result.get("success", True),
            "message": result.get("message", "修改完成"),
            "data": result
        }

    async def _execute_insert(
        self,
        order_number: Optional[str],
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行插入操作

        Args:
            order_number: 订单号
            data: 完整指令数据

        Returns:
            插入结果
        """
        if not order_number:
            return {
                "success": False,
                "error": "缺少订单号"
            }

        new_info = data.get("new_info", {})
        location = new_info.get("location")
        time = new_info.get("time")

        if not location or not time:
            return {
                "success": False,
                "error": "缺少必需的节点信息（位置和时间）"
            }

        # 调用插入 API
        result = await self._api_insert_logistics_node(
            order_number=order_number,
            location=location,
            time=time,
            **{k: v for k, v in new_info.items() if k not in ["location", "time"]}
        )

        return {
            "action": "insert",
            "success": result.get("success", True),
            "message": result.get("message", "插入完成"),
            "data": result
        }
