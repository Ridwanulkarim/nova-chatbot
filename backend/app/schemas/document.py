from typing import Optional, List, Any
from pydantic import BaseModel

class DocumentChunkOut(BaseModel):
    id: str
    chunk_index: int
    content: str
    page_number: Optional[int] = None

    class Config:
        from_attributes = True

class DocumentOut(BaseModel):
    id: str
    filename: str
    file_size: int
    mime_type: str
    chunk_count: int
    url: Optional[str] = None
    data_url: Optional[str] = None
    media_type: Optional[str] = "document"
    extracted_text: Optional[str] = None
    created_at: Any

    class Config:
        from_attributes = True
