from fastapi import APIRouter, HTTPException
import logging

from app.models.logistics_monitor import ChatRequest, ChatResponse
from app.services.logistics_service import LogisticsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/logistics", tags=["logistics"])


@router.post("/order_talk", response_model=ChatResponse, summary="物流跟踪对话")
async def order_talk(request: ChatRequest):
    """
    物流跟踪对话接口

    功能说明:
    - 处理用户关于物流跟踪的对话请求
    - 支持文本、图片等多种输入形式
    - 返回智能回复
    """
    logger.info(f"[Router] 收到物流对话请求，session_id: {request.session_id}, 内容数量: {len(request.content)}")

    try:
        # 将 Pydantic 模型转换为字典列表
        content_dicts = [item.model_dump() for item in request.content]

        result = await LogisticsService.chat(
            session_id=request.session_id,
            content=content_dicts
        )

        logger.info(f"[Router] Service 返回结果，success: {result['success']}")

        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])

        return ChatResponse(
            reply=result.get('message', '处理完成')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Router] 处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/health", summary="物流跟踪服务健康检查")
def health_check():
    """健康检查接口"""
    return {
        "service": "logistics-tracking",
        "status": "healthy",
        "description": "物流跟踪服务运行正常"
    }
