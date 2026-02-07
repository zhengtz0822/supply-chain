from app.models.base import BaseModel
from app.models.example import Example

# 导入所有模型，确保 SQLAlchemy 能够识别它们
__all__ = ["BaseModel", "Example"]
