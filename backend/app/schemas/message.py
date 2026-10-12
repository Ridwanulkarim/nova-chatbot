from typing import Optional, List, Any
from pydantic import BaseModel

class MessageCreate(BaseModel):
    content: str
    model: Optional[str] = None
    web_search: bool = False
    file_ids: Optional[List[str]] = None
    attachments: Optional[Any] = None

class MessageFeedback(BaseModel):
    feedback: int # 1 or -1

class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    model: Optional[str] = None
    citations: Optional[str] = None
    feedback: Optional[int] = None
    attachments: Optional[str] = None
    created_at: Any

    class Config:
        from_attributes = True
