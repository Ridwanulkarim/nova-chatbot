from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database.session import get_db
from app.models.user import User
from app.models.settings import UserSettings
from app.models.memory import UserMemory
from app.schemas.settings import UserSettingsUpdate, UserSettingsOut, ModelOption
from app.api.deps import get_current_user
from app.ai.provider_factory import ai_factory

router = APIRouter()

class MemoryCreate(BaseModel):
    content: str
    category: str = "preference"

class MemoryOut(BaseModel):
    id: str
    content: str
    category: str
    created_at: str

@router.get("", response_model=UserSettingsOut)
def get_user_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.patch("", response_model=UserSettingsOut)
def update_user_settings(
    settings_in: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)

    if settings_in.default_model is not None:
        settings.default_model = settings_in.default_model
    if settings_in.temperature is not None:
        settings.temperature = max(0.0, min(1.0, settings_in.temperature))
    if settings_in.system_instructions is not None:
        settings.system_instructions = settings_in.system_instructions
    if settings_in.memory_enabled is not None:
        settings.memory_enabled = settings_in.memory_enabled
    if settings_in.web_search_enabled is not None:
        settings.web_search_enabled = settings_in.web_search_enabled

    db.commit()
    db.refresh(settings)
    return settings

@router.get("/models", response_model=List[ModelOption])
def get_available_models():
    """Lists only models supported by configured providers."""
    return ai_factory.list_available_models()

@router.get("/memories", response_model=List[MemoryOut])
def get_user_memories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    memories = db.query(UserMemory).filter(UserMemory.user_id == current_user.id).all()
    return [
        {
            "id": m.id,
            "content": m.content,
            "category": m.category,
            "created_at": m.created_at.isoformat()
        }
        for m in memories
    ]

@router.post("/memories", response_model=MemoryOut)
def create_user_memory(
    memory_in: MemoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    memory = UserMemory(
        user_id=current_user.id,
        content=memory_in.content.strip(),
        category=memory_in.category
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return {
        "id": memory.id,
        "content": memory.content,
        "category": memory.category,
        "created_at": memory.created_at.isoformat()
    }

@router.delete("/memories/{memory_id}")
def delete_user_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    memory = db.query(UserMemory).filter(
        UserMemory.id == memory_id,
        UserMemory.user_id == current_user.id
    ).first()
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory record not found"
        )
    db.delete(memory)
    db.commit()
    return {"message": "Memory removed"}
