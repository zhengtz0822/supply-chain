from agentscope.tool import Toolkit
from .mcp_clients import create_gaode_mcp_client
import logging

# 全局 Toolkit 实例（可选，也可按需创建）
# toolkit = Toolkit()

# async def initialize_tools():
#     """异步初始化所有 MCP 工具"""
#     # 创建工具组
#     toolkit.create_tool_group("amps", description="高德地图工具组")
#     client = create_gaode_mcp_client()
#     await toolkit.register_mcp_client(client, group_name="amps")  # 可选分组
#     # 激活工具组
#     toolkit.update_tool_groups(["amps"], active=True)
#     # print(f"✅ 注册了 {len(toolkit.get_json_schemas())} 个 MCP 工具")
#     logging.info(f"✅ 注册了 {len(toolkit.get_json_schemas())} 个 MCP 工具")
#     # 打印工具schema
#     for schema in toolkit.get_json_schemas():
#         logging.info(f"工具 Schema 信息: {schema}")


async def create_fresh_toolkit() -> Toolkit:
    """创建一个全新的、已初始化的 Toolkit"""
    toolkit = Toolkit()
    toolkit.create_tool_group("amps", description="高德地图工具组")

    # 每次都新建 MCP 客户端（确保无状态）
    client = create_gaode_mcp_client()
    await toolkit.register_mcp_client(client, group_name="amps")
    toolkit.update_tool_groups(["amps"], active=True)

    logging.info(f"✅ 创建新 Toolkit，注册了 {len(toolkit.get_json_schemas())} 个工具")
    return toolkit


# def get_toolkit() -> Toolkit:
#     return toolkit