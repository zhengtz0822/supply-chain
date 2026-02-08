from agentscope.mcp import HttpStatelessClient
from app.core.config import get_settings

# 创建高德地图mcp客户端
def create_gaode_mcp_client():
    return HttpStatelessClient(
        name="gaode_maps",
        transport="streamable_http",
        url=f"{get_settings().AMAP_MCP_URL}?key={get_settings().AMAP_APP_KEY}",
    )