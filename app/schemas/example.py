from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ExampleBase(BaseModel):
    """Example 基础 Schema"""
    name: str = Field(..., max_length=100, description="名称")
    code: str = Field(..., max_length=50, description="编码")
    description: Optional[str] = Field(None, description="描述")
    price: float = Field(0.0, ge=0, description="价格")
    is_active: bool = Field(True, description="是否启用")


class ExampleCreate(ExampleBase):
    """创建 Example 的 Schema"""
    pass


class ExampleUpdate(BaseModel):
    """更新 Example 的 Schema - 所有字段可选"""
    name: Optional[str] = Field(None, max_length=100, description="名称")
    description: Optional[str] = Field(None, description="描述")
    price: Optional[float] = Field(None, ge=0, description="价格")
    is_active: Optional[bool] = Field(None, description="是否启用")


class ExampleResponse(ExampleBase):
    """Example 响应 Schema"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2


class ExampleListResponse(BaseModel):
    """Example 列表响应 Schema"""
    total: int
    items: list[ExampleResponse]
