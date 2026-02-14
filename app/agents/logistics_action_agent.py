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
from app.core.config import get_settings
from typing import Optional, Dict, Any

import httpx
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
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_settings().API_BASE_URL}/orderInfoService/getOrderInfo?orderNo={order_number}"
            )
            return response.json()

        # 模拟返回数据
        # logger.info(f"[Actor] 调用查询API: {order_number}")
        # return {
        #     "order_number": order_number,
        #     "status": "在途中",
        #     "current_location": "北京转运中心",
        #     "estimated_delivery": "2024-01-15",
        #     "history": [
        #         {"time": "2024-01-10 10:00", "location": "深圳", "status": "已揽收"},
        #         {"time": "2024-01-12 08:00", "location": "武汉", "status": "运输中"},
        #         {"time": "2024-01-13 15:00", "location": "北京", "status": "到达"},
        #     ]
        # }

    async def _api_modify_logistics(
        self,
        session_id: Optional[str] = None,
        order_id: Optional[str] = None,
        order_number: Optional[str] = None,
        transport_status_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        修改物流信息（伪代码）

        Args:
            session_id: 会话ID（用于审计追踪）
            order_id: 订单ID（数据库唯一标识）
            order_number: 订单编号（业务编号）
            transport_status_name: 运输状态（待提货/运输中/已送达/已回单/异常滞留）
            **kwargs: 其他修改参数

        Returns:
            操作结果
        """
        # TODO: 接入真实业务 API
        # 示例伪代码:
        # async with httpx.AsyncClient() as client:
        #     payload = {
        #         "transportStatusName": transport_status_name,
        #         "sessionId": session_id  # 会话ID用于审计日志
        #     }
        #     if order_id:
        #         payload["id"] = order_id
        #     if order_number:
        #         payload["orderNumber"] = order_number
        #
        #     response = await client.post(
        #         f"{get_settings().API_BASE_URL}/orderInfoService/updateOrderInfo",
        #         json=payload
        #     )
        #     return response.json()

        # 模拟返回数据
        logger.info(f"[Actor] 调用修改API: session_id={session_id}, order_id={order_id}, order_number={order_number} -> {transport_status_name}")
        return {
            "success": True,
            "session_id": session_id,
            "order_id": order_id,
            "order_number": order_number,
            "transport_status_name": transport_status_name,
            "message": f"物流状态已更新为: {transport_status_name}",
            "updated_at": "2024-01-13 16:00"
        }

    async def _api_modify_logistics_node(
        self,
        order_id: str,
        session_id: str,
        tracking_id: str,
        location: str,
        status_description: Optional[str] = None,
        operator: Optional[str] = None,
        vehicle_plate: Optional[str] = None,
        occurred_at_str: Optional[str] = None,
        remark: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        修改物流节点信息（伪代码）

        Args:
            order_id: 订单ID（从查询结果获取）
            session_id: 会话ID（用于审计追踪）
            tracking_id: 物流轨迹ID（数据库唯一标识）
            location: 发生地点（必要参数）
            status_description: 状态描述（可选）
            operator: 操作人（可选）
            vehicle_plate: 车牌号（可选）
            occurred_at_str: 发生时间（可选，格式: yyyy-MM-dd）
            remark: 备注（可选）
            content: 物流信息（可选，如"货物已送达收货地点"、"货物已从中转站发出"等自定义信息）
            **kwargs: 其他参数

        Returns:
            操作结果
        """
        # 接入真实业务 API
        async with httpx.AsyncClient() as client:
            payload = {
                "orderId": order_id,              # 订单ID
                "sessionId": session_id,            # 会话ID用于审计日志
                "id": tracking_id,                 # 物流轨迹ID
                "location": location,               # 发生地点
            }
            if status_description:
                payload["statusDescription"] = status_description
            if operator:
                payload["operator"] = operator
            if vehicle_plate:
                payload["vehiclePlate"] = vehicle_plate
            if occurred_at_str:
                payload["occurredAtStr"] = occurred_at_str
            if remark:
                payload["remark"] = remark
            if content:
                payload["content"] = content
        
            response = await client.post(
                f"{get_settings().API_BASE_URL}/orderInfoService/updateLogisticsTrackInfo",
                json=payload
            )
        #     return response.json()

        # 模拟返回数据
        logger.info(
            f"[Actor] 调用修改物流节点API，请求参数: order_id={order_id}, session_id={session_id}, "
            f"tracking_id={tracking_id}, location={location}"
        )
        return {
            "success": True,
            "order_id": order_id,
            "session_id": session_id,
            "tracking_id": tracking_id,
            "location": location,
            "status_description": status_description,
            "operator": operator,
            "vehicle_plate": vehicle_plate,
            "occurred_at_str": occurred_at_str,
            "remark": remark,
            "content": content,
            "message": f"物流节点已更新: {location}",
            "updated_at": "2024-01-13 16:00"
        }

    async def _api_insert_logistics_node(
        self,
        order_id: str,
        status_description: str,
        location: str,
        occurred_at_str: str,
        session_id: str,
        operator: Optional[str] = None,
        vehicle_plate: Optional[str] = None,
        remark: Optional[str] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        插入物流节点（伪代码）

        Args:
            order_id: 订单唯一ID（必填）
            status_description: 物流状态描述（必填）
            location: 发生地点（必填）
            occurred_at_str: 发生时间（必填，格式: yyyy-MM-dd）
            session_id: 会话ID（用于审计追踪）
            operator: 操作人（可选）
            vehicle_plate: 车牌号（可选）
            remark: 备注（可选）
            content: 物流信息（可选，如"货物已送达收货地点"、"货物已从中转站发出"等自定义信息）
            **kwargs: 其他参数

        Returns:
            操作结果
        """
        # 接入真实业务 API
        async with httpx.AsyncClient() as client:
            payload = {
                "orderId": order_id,              # 订单唯一ID
                "sessionId": session_id,            # 会话ID用于审计日志
                "statusDescription": status_description,  # 物流状态描述
                "location": location,              # 发生地点
                "occurredAtStr": occurred_at_str,   # 发生时间
            }
            if operator:
                payload["operator"] = operator
            if vehicle_plate:
                payload["vehiclePlate"] = vehicle_plate
            if remark:
                payload["remark"] = remark
            if content:
                payload["content"] = content
        
            response = await client.post(
                f"{get_settings().API_BASE_URL}/orderInfoService/insertLogisticsTrackInfo",
                json=payload
            )
            return response.json()

        # 模拟返回数据
        logger.info(
            f"[Actor] 调用插入物流节点API: order_id={order_id}, "
            f"status_description={status_description}, location={location}, occurred_at_str={occurred_at_str}"
        )
        return {
            "success": True,
            "order_id": order_id,
            "status_description": status_description,
            "location": location,
            "occurred_at_str": occurred_at_str,
            "operator": operator,
            "vehicle_plate": vehicle_plate,
            "remark": remark,
            "content": content,
            "node_id": "NODE_" + str(hash(location + occurred_at_str)),
            "message": f"已插入新节点: {location}",
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
                   "action": "query" | "modify" | "modify_node" | "insert",
                   ...
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

            # 根据操作类型执行
            if action == "query":
                result = await self._execute_query(data.get("order_number"), data)

            elif action == "modify":
                # 兼容旧的修改运输状态操作
                result = await self._execute_modify(data.get("order_number"), data)

            elif action == "modify_node":
                # 新增：修改物流节点信息
                result = await self._execute_modify_node(data)

            elif action == "insert":
                # 插入物流节点信息
                result = await self._execute_insert(data)

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
            order_number: 订单号（保留兼容性）
            data: 完整指令数据，包含:
                - session_id: 会话ID（用于审计追踪）
                - order_id: 订单ID（可选）
                - order_number: 订单编号（可选）
                - transport_status_name: 运输状态（必填）

        Returns:
            修改结果
        """
        # 提取参数
        session_id = data.get("session_id")
        order_id = data.get("order_id")
        order_number = data.get("order_number") or order_number
        transport_status_name = data.get("transport_status_name")

        # 验证必填参数
        if not order_id and not order_number:
            return {
                "success": False,
                "error": "缺少订单标识（order_id 或 order_number）"
            }

        if not transport_status_name:
            return {
                "success": False,
                "error": "缺少运输状态（transport_status_name）"
            }

        # 验证状态值是否合法
        valid_statuses = ["待提货", "运输中", "已送达", "已回单", "异常滞留"]
        if transport_status_name not in valid_statuses:
            return {
                "success": False,
                "error": f"无效的运输状态，可选值: {', '.join(valid_statuses)}"
            }

        # 调用修改 API
        result = await self._api_modify_logistics(
            session_id=session_id,
            order_id=order_id,
            order_number=order_number,
            transport_status_name=transport_status_name
        )

        return {
            "action": "modify",
            "success": result.get("success", True),
            "message": result.get("message", "修改完成"),
            "data": result
        }

    async def _execute_modify_node(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行修改物流节点操作

        Args:
            data: 完整指令数据，包含:
                - order_id: 订单ID（必填，从查询结果获取）
                - session_id: 会话ID（用于审计追踪）
                - tracking_id: 物流轨迹ID（必填）
                - node_location: 发生地点（必填）
                - status_description: 状态描述（可选）
                - operator: 操作人（可选）
                - vehicle_plate: 车牌号（可选）
                - occurred_at_str: 发生时间（可选，格式: yyyy-MM-dd）
                - remark: 备注（可选）
                - content: 物流信息（可选）

        Returns:
            修改结果
        """
        # 提取参数
        order_id = data.get("order_id")
        session_id = data.get("session_id")
        tracking_id = data.get("tracking_id")
        node_location = data.get("node_location")
        status_description = data.get("status_description")
        operator = data.get("operator")
        vehicle_plate = data.get("vehicle_plate")
        occurred_at_str = data.get("occurred_at_str")
        remark = data.get("remark")
        content = data.get("content")

        # 验证必填参数
        if not order_id:
            return {
                "success": False,
                "error": "缺少订单ID（order_id）"
            }

        if not session_id:
            return {
                "success": False,
                "error": "缺少会话ID（session_id）"
            }

        if not tracking_id:
            return {
                "success": False,
                "error": "缺少物流轨迹ID（tracking_id）"
            }

        if not node_location:
            return {
                "success": False,
                "error": "缺少发生地点（node_location）"
            }

        # 验证日期格式
        if occurred_at_str:
            import re
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            if not re.match(date_pattern, occurred_at_str):
                return {
                    "success": False,
                    "error": "日期格式错误，应为 yyyy-MM-dd 格式"
                }

        # 调用修改物流节点 API
        result = await self._api_modify_logistics_node(
            order_id=order_id,
            session_id=session_id,
            tracking_id=tracking_id,
            location=node_location,
            status_description=status_description,
            operator=operator,
            vehicle_plate=vehicle_plate,
            occurred_at_str=occurred_at_str,
            remark=remark,
            content=content
        )

        return {
            "action": "modify_node",
            "success": result.get("success", True),
            "message": result.get("message", "物流节点修改完成"),
            "data": result
        }

    async def _execute_insert(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行插入物流节点操作

        Args:
            data: 完整指令数据，包含:
                - order_id: 订单唯一ID（必填）
                - session_id: 会话ID（用于审计追踪）
                - status_description: 物流状态描述（必填）
                - node_location: 发生地点（必填）
                - occurred_at_str: 发生时间（必填，格式: yyyy-MM-dd）
                - operator: 操作人（可选）
                - vehicle_plate: 车牌号（可选）
                - remark: 备注（可选）
                - content: 物流信息（可选）

        Returns:
            插入结果
        """
        # 提取参数
        order_id = data.get("order_id")
        session_id = data.get("session_id")
        status_description = data.get("status_description")
        node_location = data.get("node_location")
        occurred_at_str = data.get("occurred_at_str")
        operator = data.get("operator")
        vehicle_plate = data.get("vehicle_plate")
        remark = data.get("remark")
        content = data.get("content")

        # 验证必填参数
        if not order_id:
            return {
                "success": False,
                "error": "缺少订单唯一ID（order_id）"
            }

        if not status_description:
            return {
                "success": False,
                "error": "缺少物流状态描述（status_description）"
            }

        if not node_location:
            return {
                "success": False,
                "error": "缺少发生地点（node_location）"
            }

        if not occurred_at_str:
            return {
                "success": False,
                "error": "缺少发生时间（occurred_at_str）"
            }

        # 验证日期格式
        import re
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(date_pattern, occurred_at_str):
            return {
                "success": False,
                "error": "日期格式错误，应为 yyyy-MM-dd 格式"
            }

        # 调用插入物流节点 API
        result = await self._api_insert_logistics_node(
            order_id=order_id,
            session_id=session_id,
            location=node_location,
            occurred_at_str=occurred_at_str,
            status_description=status_description,
            operator=operator,
            vehicle_plate=vehicle_plate,
            remark=remark,
            content=content
        )

        return {
            "action": "insert",
            "success": result.get("success", True),
            "message": result.get("message", "物流节点插入完成"),
            "data": result
        }
