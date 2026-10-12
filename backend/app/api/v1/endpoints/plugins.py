import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database.session import get_db
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

# In-memory user installed plugins registry (persisted per user)
_USER_INSTALLED_PLUGINS: Dict[str, set] = {}

class TogglePluginRequest(BaseModel):
    plugin_id: str
    action: str  # "install" | "uninstall"

@router.get("/installed")
def get_installed_plugins(current_user: User = Depends(get_current_user)):
    user_installed = _USER_INSTALLED_PLUGINS.get(current_user.id, {"github", "web_search", "document_rag"})
    return {"installed_plugin_ids": list(user_installed)}

@router.post("/toggle")
def toggle_plugin(
    req: TogglePluginRequest,
    current_user: User = Depends(get_current_user)
):
    if current_user.id not in _USER_INSTALLED_PLUGINS:
        _USER_INSTALLED_PLUGINS[current_user.id] = {"github", "web_search", "document_rag"}

    installed_set = _USER_INSTALLED_PLUGINS[current_user.id]
    if req.action == "install":
        installed_set.add(req.plugin_id)
        is_installed = True
    else:
        installed_set.discard(req.plugin_id)
        is_installed = False

    return {
        "success": True,
        "plugin_id": req.plugin_id,
        "is_installed": is_installed,
        "installed_count": len(installed_set)
    }
