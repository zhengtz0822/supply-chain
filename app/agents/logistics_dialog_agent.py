# agents/logistics_dialog_agent.py
"""
对话智能体 - Dialog

职责:
- 与用户进行自然语言交互
- 将执行结果转换为用户友好的回复
- 根据不同场景生成合适的回复
- 引导用户提供缺失信息
"""
import logging
import json
from typing import Optional, Dict, Any
from agentscope.agent import ReActAgent
from agentscope.message import Msg

logger = logging.getLogger(__name__)


class LogisticsDialogAgent(ReActAgent):
    """
    物流对话智能体

    功能:
    1. 将系统执行结果转换为自然语言回复
    2. 向用户询问缺失信息
    3. 引导用户完成复杂操作
    4. 处理异常情况和错误提示
    """

    def __init__(self, model_config, formatter, **kwargs):
        super().__init__(
            name="Dialog",
            sys_prompt="""你是一个专业的物流客服助手，负责与用户进行友好、专业的对话。

## 核心职责
1. **结果呈现**: 将系统执行结果转换为用户友好的自然语言
2. **信息收集**: 当信息不足时，主动询问用户所需信息
3. **异常处理**: 遇到错误时给出清晰的解释和建议
4. **流程引导**: 引导用户完成复杂的物流操作

## 回复风格
- 友好、专业、简洁
- 使用emoji增强可读性
- 结构化呈现复杂信息
- 主动提供下一步操作建议

## 场景处理

### 1. 查询结果呈现
```
📦 订单号: order1234567890

当前状态: 在途中 🚚
当前位置: 北京转运中心
预计送达: 2024-01-15

物流轨迹:
• 2024-01-10 10:00 深圳 - 已揽收
• 2024-01-12 08:00 武汉 - 运输中
• 2024-01-13 15:00 北京 - 已到达

还需要其他帮助吗？
```

### 2. 修改成功确认
```
✅ 修改成功！

订单号: order1234567890
状态已更新为: 已送达
更新时间: 2024-01-13 16:00

如需查询最新状态，可以说"查一下这个订单"
```

### 3. 插入节点成功
```
✅ 物流节点已添加

订单号: order1234567890
新节点: 北京转运中心
时间: 2024-01-13 16:00
车牌: 京A12345

还有其他信息需要补充吗？
```

### 4. 信息不足询问
```
🤔 为了帮您完成操作，还需要一些信息：

❓ 请问您要修改成什么状态？
   可选状态: 运输中、已送达、异常等

❓ 订单号是多少？

请提供以上信息，我将立即为您处理。
```

### 5. 错误处理
```
❌ 操作失败

原因: [错误信息]

建议:
• 检查订单号是否正确
• 确认是否有操作权限
• 稍后重试或联系人工客服

需要其他帮助吗？
```

## 注意事项
- 始终保持礼貌和耐心
- 使用简单易懂的语言，避免技术术语
- 对于敏感操作（修改、删除），二次确认
- 记住对话上下文，支持连续对话
""",
            model=model_config,
            formatter=formatter,
            **kwargs
        )
        logger.info("[Dialog] 物流对话智能体已初始化")

    async def format_response(
        self,
        reasoning_result: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]] = None
    ) -> Msg:
        """
        格式化响应消息

        Args:
            reasoning_result: 推理智能体的结果
            execution_result: 执行智能体的结果（如果有）

        Returns:
            格式化后的用户回复
        """
        logger.info(f"[Dialog] 格式化响应，意图: {reasoning_result.get('intent')}")

        # 构建输入
        dialog_input = self._build_dialog_input(reasoning_result, execution_result)

        # 创建对话消息
        dialog_msg = Msg(
            name="user",
            content=dialog_input,
            role="user"
        )

        try:
            # 调用模型生成回复
            response_msg: Msg = await self(dialog_msg)

            logger.info(f"[Dialog] 生成回复: {response_msg.content[:100]}...")
            return response_msg

        except Exception as e:
            logger.error(f"[Dialog] 生成回复失败: {e}", exc_info=True)
            # 返回一个错误回复
            return Msg(
                name=self.name,
                content=f"抱歉，处理您的请求时遇到了问题: {str(e)}",
                role="assistant"
            )

    def _build_dialog_input(
        self,
        reasoning_result: Dict[str, Any],
        execution_result: Optional[Dict[str, Any]]
    ) -> str:
        """
        构建对话输入

        Args:
            reasoning_result: 推理结果
            execution_result: 执行结果

        Returns:
            格式化的输入字符串
        """
        parts = []

        intent = reasoning_result.get("intent", "unknown")
        parts.append(f"## 用户意图: {intent}")

        # 推理信息
        if reasoning_result.get("reasoning"):
            parts.append(f"\n## 推理过程:")
            parts.append(reasoning_result["reasoning"])

        # 澄清问题
        if intent == "clarify":
            questions = reasoning_result.get("clarification_questions", [])
            if questions:
                parts.append(f"\n## 需要向用户询问的问题:")
                for i, q in enumerate(questions, 1):
                    parts.append(f"{i}. {q}")

        # 执行结果
        if execution_result:
            parts.append(f"\n## 执行结果:")
            parts.append(f"```json")
            parts.append(json.dumps(execution_result, ensure_ascii=False, indent=2))
            parts.append(f"```")

        parts.append("\n请根据以上信息，生成用户友好的回复。")

        return "\n".join(parts)

    def format_clarification_questions(self, questions: list[str]) -> str:
        """
        格式化澄清问题（辅助方法）

        Args:
            questions: 问题列表

        Returns:
            格式化的问题字符串
        """
        if not questions:
            return ""

        lines = ["🤔 为了帮您完成操作，还需要一些信息:\n"]
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. {q}")
        lines.append("\n请提供以上信息，我将立即为您处理。")

        return "\n".join(lines)

    def format_logistics_info(self, logistics_data: Dict[str, Any]) -> str:
        """
        格式化物流信息（辅助方法）

        Args:
            logistics_data: 物流数据

        Returns:
            格式化的物流信息字符串
        """
        lines = [
            f"📦 订单号: {logistics_data.get('order_number', '未知')}",
            "",
            f"当前状态: {logistics_data.get('status', '未知')} 🚚",
            f"当前位置: {logistics_data.get('current_location', '未知')}",
            f"预计送达: {logistics_data.get('estimated_delivery', '未知')}",
            "",
            "物流轨迹:"
        ]

        history = logistics_data.get("history", [])
        for item in history:
            lines.append(
                f"• {item.get('time', '')} {item.get('location', '')} - {item.get('status', '')}"
            )

        lines.append("\n还需要其他帮助吗？")

        return "\n".join(lines)
