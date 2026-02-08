from agentscope.tool import Toolkit
from .mcp_clients import create_gaode_mcp_client
import logging

# 全局 Toolkit 实例（可选，也可按需创建）
toolkit = Toolkit()

async def initialize_tools():
    """异步初始化所有 MCP 工具"""
    # 创建工具组
    toolkit.create_tool_group("amps", description="高德地图工具组")
    client = create_gaode_mcp_client()
    await toolkit.register_mcp_client(client, group_name="amps")  # 可选分组
    # 激活工具组
    toolkit.update_tool_groups(["amps"], active=True)
    # print(f"✅ 注册了 {len(toolkit.get_json_schemas())} 个 MCP 工具")
    logging.info(f"✅ 注册了 {len(toolkit.get_json_schemas())} 个 MCP 工具")

def get_toolkit() -> Toolkit:
    return toolkit