from fastapi import APIRouter, HTTPException
import os
import logging

from app.schemas.address import (
    AddressParseRequest,
    AddressParseResponse,
    AddressParseData,
    AddressMatchRequest,
    AddressMatchResponse
)
from app.services.address_service import AddressService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/address", tags=["address"])


@router.post("/parse", response_model=AddressParseResponse, summary="解析地址数据")
def parse_addresses(request: AddressParseRequest):
    """
    从CSV或Excel文件中解析地址数据

    功能说明:
    - 支持读取 .csv 和 .xlsx 文件
    - 自动识别地址列
    - 提取并去重地址数据
    - 输出到CSV文件（UTF-8-BOM编码）

    地址列识别规则:
    - 文本长度在 5 到 100 个字符之间
    - 不包含 @、/、\\ 等邮箱或路径符号
    - 不是纯数字
    - 至少有 2 行包含中文地址关键词（省、市、区、街道、路、号等）
    - 列名不能是 ID、编号、序号等明显非地址字段
    """
    logger.info(f"[Router] 收到地址解析请求，batchId: {request.batchId}, 文件数量: {len(request.localAttachments)}")
    logger.info(f"[Router] 文件路径: {request.localAttachments}")

    if not request.localAttachments:
        logger.error("[Router] 文件路径列表为空")
        raise HTTPException(status_code=400, detail="文件路径列表不能为空")

    # 验证文件是否存在
    for file_path in request.localAttachments:
        if not os.path.exists(file_path):
            logger.error(f"[Router] 文件不存在: {file_path}")
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

    logger.info(f"[Router] 文件验证通过，开始调用 Service...")

    try:
        result = AddressService.parse_addresses_from_files(
            batch_id=request.batchId,
            file_paths=request.localAttachments
        )
        logger.info(f"[Router] Service 返回结果，success: {result['success']}")

        # 构建响应数据
        data = None
        if result['success'] and result['refinement_result']:
            logger.info(f"[Router] 构建响应数据，结果数: {len(result['refinement_result'].results)}")
            data = AddressParseData(
                batchId=request.batchId,
                results=result['refinement_result'].results
            )

        return AddressParseResponse(
            success=result['success'],
            message=result['message'],
            data=data
        )

    except FileNotFoundError as e:
        logger.error(f"[Router] 文件未找到: {str(e)}")
        return AddressParseResponse(
            success=False,
            message=f"文件未找到: {str(e)}",
            data=None
        )
    except ValueError as e:
        logger.error(f"[Router] 参数错误: {str(e)}")
        return AddressParseResponse(
            success=False,
            message=f"参数错误: {str(e)}",
            data=None
        )
    except Exception as e:
        logger.error(f"[Router] 处理失败: {str(e)}", exc_info=True)
        return AddressParseResponse(
            success=False,
            message=f"处理失败: {str(e)}",
            data=None
        )


@router.get("/health", summary="地址解析服务健康检查")
def health_check():
    """健康检查接口"""
    return {
        "service": "address-parse",
        "status": "healthy",
        "description": "地址解析服务运行正常"
    }


@router.post("/match", response_model=AddressMatchResponse, summary="地址匹配度分析")
def match_addresses(request: AddressMatchRequest):
    """
    地址匹配度分析

    功能说明:
    - 分析源地址与候选地址的匹配度
    - 判断是否描述同一地理位置
    - 提供优化建议和置信度评分

    TODO: 具体逻辑待实现
    """
    logger.info(f"[Router] 收到地址匹配请求，源地址: {request.source.address_text}, 候选数量: {len(request.candidates)}")

    if not request.candidates:
        logger.error("[Router] 候选地址列表为空")
        return AddressMatchResponse(
            success=False,
            message="候选地址列表不能为空",
            data=None
        )

    try:
        result = AddressService.match_addresses(
            source=request.source,
            candidates=request.candidates,
            task_config=request.task_config
        )

        return AddressMatchResponse(
            success=result['success'],
            message=result['message'],
            data=result.get('result')
        )

    except NotImplementedError as e:
        logger.error(f"[Router] 功能未实现: {str(e)}")
        return AddressMatchResponse(
            success=False,
            message=f"功能待实现: {str(e)}",
            data=None
        )
    except Exception as e:
        logger.error(f"[Router] 处理失败: {str(e)}", exc_info=True)
        return AddressMatchResponse(
            success=False,
            message=f"处理失败: {str(e)}",
            data=None
        )
