from pydantic import BaseModel, Field
from typing import List, Optional, Generic, TypeVar


# 地址列信息（用于内部处理）
class AddressColumnInfo(BaseModel):
    """地址列信息"""
    column_name: str = Field(..., description="列名")
    sample_count: int = Field(..., description="采样数量")
    keyword_match_count: int = Field(..., description="匹配关键词数量")


# LLM 处理结果模型（与 service 中的定义保持一致）
class AddressResultItem(BaseModel):
    """单个地址识别结果"""
    text: str = Field(..., description="处理后的地址文本")
    location: bool = Field(..., description="是否为位置信息")


class AddressRefinementData(BaseModel):
    """地址识别数据"""
    results: List[AddressResultItem] = Field(..., description="地址识别结果列表")


# 通用响应包装器
T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """通用 API 响应结构"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    data: Optional[T] = Field(None, description="响应数据")


# 具体请求/响应模型
class AddressParseRequest(BaseModel):
    """地址解析请求 Schema"""
    batchId: str = Field(..., description="批次ID")
    localAttachments: List[str] = Field(..., description="本地文件路径数组")


class AddressParseData(BaseModel):
    """地址解析数据"""
    batchId: str = Field(..., description="批次ID")
    results: List[AddressResultItem] = Field(..., description="地址识别结果列表")


# 响应类型定义
AddressParseResponse = ApiResponse[AddressParseData]


# 地址匹配相关模型
class AddressMatchSource(BaseModel):
    """源地址信息"""
    address_text: Optional[str] = Field(..., description="原始地址文本")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")


class AddressMatchCandidate(BaseModel):
    """候选地址信息"""
    candidate_id: Optional[str] = Field(None, description="候选POI ID")
    address_text: Optional[str] = Field(None, description="地址文本")
    actualAddress: Optional[str] = Field(None, description="完整结构化地址")
    firstLevelAddress: Optional[str] = Field(None, description="一级地址（如建筑物名称）")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")


class AddressMatchTaskConfig(BaseModel):
    """匹配任务配置"""
    distance_threshold_meters: float = Field(100, description="距离阈值（米）")
    use_text_similarity: bool = Field(True, description="是否使用文本相似度")


class AddressMatchRequest(BaseModel):
    """地址匹配请求 Schema"""
    source: Optional[AddressMatchSource] = Field(..., description="源地址信息")
    candidates: Optional[List[AddressMatchCandidate]] = Field(..., description="候选地址列表")
    task_config: Optional[AddressMatchTaskConfig] = Field(None, description="任务配置")


class AddressSource(BaseModel):
    """地址源信息"""
    address_text: Optional[str] = Field(..., description="原始地址文本")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")


class AddressRecommendation(BaseModel):
    """地址建议"""
    action: str = Field(..., description="建议(新地址、相似地址)")
    suggested_candidate_id: Optional[str] = Field(None, description="建议采用的候选POI ID（如果action为相似地址）")
    suggested_address_text: Optional[str] = Field(None, description="建议采用的地址文本")
    overall_confidence: float = Field(..., description="整体置信度 0-1")
    reason: str = Field(..., description="建议原因")


class AddressMatch(BaseModel):
    """地址匹配结果"""
    candidate_id: str = Field(..., description="候选ID")
    address_text: str = Field(..., description="候选地址文本")
    is_same_location: bool = Field(..., description="是否同一位置")
    confidence_score: float = Field(..., description="置信度分数 0-1")
    distance_meters: Optional[float] = Field(None, description="距离（米）")
    reason: str = Field(..., description="匹配原因")


class AddressMatchResult(BaseModel):
    """地址匹配结果"""
    source: AddressSource = Field(..., description="地址源信息")
    recommendation: AddressRecommendation = Field(..., description="全局推荐信息")
    matches: List[AddressMatch] = Field(default_factory=list, description="匹配的候选POI列表")


AddressMatchResponse = ApiResponse[AddressMatchResult]
