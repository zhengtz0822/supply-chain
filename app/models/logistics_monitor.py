# models.py
from pydantic import BaseModel, Field
from typing import List, Union, Literal

class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str

class ImageUrlContent(BaseModel):
    type: Literal["image_url"] = "image_url"
    image_url: str

class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    image: str  # base64

ContentItem = Union[TextContent, ImageUrlContent, ImageContent]

class ChatRequest(BaseModel):
    session_id: str = Field(alias="sessionId", description="会话ID")
    content: List[ContentItem] = Field(..., min_items=1)

    class Config:
        populate_by_name = True  # 允许使用别名和字段名

class ChatResponse(BaseModel):
    reply: str