from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.deps import get_current_user
from app.models.user import User
from app.ai.search_service import search_service

router = APIRouter()

class SearchRequest(BaseModel):
    query: str

@router.post("", response_model=List[Dict[str, Any]])
async def perform_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    return await search_service.search(request.query)
