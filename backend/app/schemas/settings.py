from typing import Optional, List
from pydantic import BaseModel

class UserSettingsUpdate(BaseModel):
    default_model: Optional[str] = None
    temperature: Optional[float] = None
    system_instructions: Optional[str] = None
    memory_enabled: Optional[bool] = None
    web_search_enabled: Optional[bool] = None

class UserSettingsOut(BaseModel):
    user_id: str
    default_model: str
    temperature: float
    system_instructions: str
    memory_enabled: bool
    web_search_enabled: bool

    class Config:
        from_attributes = True

class ModelOption(BaseModel):
    id: str
    name: str
    provider: str
    description: str
    context_window: int
    supports_vision: bool
    supports_streaming: bool
