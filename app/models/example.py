from sqlalchemy import Column, String, Float, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Example(BaseModel):
    """
    示例模型
    你可以根据实际需求修改这个模型
    """
    __tablename__ = "examples"

    # 字段定义
    name = Column(String(100), nullable=False, index=True, comment="名称")
    code = Column(String(50), unique=True, nullable=False, index=True, comment="编码")
    description = Column(Text, nullable=True, comment="描述")
    price = Column(Float, default=0.0, comment="价格")
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 关系定义 (示例)
    # items = relationship("Item", back_populates="category")

    def __repr__(self):
        return f"<Example(id={self.id}, name={self.name}, code={self.code})>"
