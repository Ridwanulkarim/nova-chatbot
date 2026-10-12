from typing import Optional, List, Any
from pydantic import BaseModel
from app.schemas.message import MessageOut

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Chat"
    model: Optional[str] = None
    system_prompt: Optional[str] = None

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None

class ConversationOut(BaseModel):
    id: str
    user_id: str
    title: str
    model: str
    system_prompt: Optional[str] = None
    is_pinned: bool
    is_archived: bool
    share_token: Optional[str] = None
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True

class ConversationDetail(ConversationOut):
    messages: List[MessageOut] = []
