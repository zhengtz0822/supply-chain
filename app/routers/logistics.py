from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import logging
import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from app.models.logistics_monitor import ChatRequest, ChatResponse, StreamChatResponse
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

@router.post("/order_talk_stream", summary="物流跟踪对话(流式)")
async def order_talk_stream(request: ChatRequest):
    """
    物流跟踪对话接口(流式返回)
    
    功能说明:
    - 处理用户关于物流跟踪的对话请求
    - 支持文本、图片等多种输入形式
    - **真正流式返回**：Dialog Agent 逐字生成回复
    """
    logger.info(f"[Router Stream] 收到物流对话请求，session_id: {request.session_id}, 内容数量: {len(request.content)}")
    
    async def generate_response() -> AsyncGenerator[str, None]:
        """生成流式响应"""
        try:
            # 将 Pydantic 模型转换为字典列表
            content_dicts = [item.model_dump() for item in request.content]
            
            # 发送开始信号
            start_data = StreamChatResponse(
                type="start",
                content="开始处理您的请求...",
                session_id=request.session_id,
                timestamp=datetime.now().isoformat()
            )
            yield f"data: {json.dumps(start_data.model_dump(), ensure_ascii=False)}\n\n"
            
            # 调用物流服务的流式方法
            # 现在 chat_stream 返回的是异步生成器，逐块产生内容
            chunk_index = 0
            async for chunk in LogisticsService.chat_stream(
                session_id=request.session_id,
                content=content_dicts
            ):
                chunk_index += 1
                chunk_data = StreamChatResponse(
                    type="chunk",
                    content=chunk,
                    session_id=request.session_id,
                    timestamp=datetime.now().isoformat()
                )
                yield f"data: {json.dumps(chunk_data.model_dump(), ensure_ascii=False)}\n\n"
            
            logger.info(f"[Router Stream] 流式响应完成，共 {chunk_index} 个 chunk")
            
            # 发送完成信号
            complete_data = StreamChatResponse(
                type="complete",
                content="",
                session_id=request.session_id,
                timestamp=datetime.now().isoformat()
            )
            yield f"data: {json.dumps(complete_data.model_dump(), ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"[Router Stream] 处理失败: {str(e)}", exc_info=True)
            error_data = StreamChatResponse(
                type="error",
                content=f"处理失败: {str(e)}",
                session_id=request.session_id,
                timestamp=datetime.now().isoformat()
            )
            yield f"data: {json.dumps(error_data.model_dump(), ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@router.get("/health", summary="物流跟踪服务健康检查")
def health_check():
    """健康检查接口"""
    return {
        "service": "logistics-tracking",
        "status": "healthy",
        "description": "物流跟踪服务运行正常"
    }
