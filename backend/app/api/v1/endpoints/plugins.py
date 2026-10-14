from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database.session import get_db
from app.models.user import User
from app.models.plugin import UserPlugin
from app.api.deps import get_current_user

router = APIRouter()

DEFAULT_PLUGINS = ["github", "web_search", "document_rag"]

class TogglePluginRequest(BaseModel):
    plugin_id: str
    action: str  # "install" | "uninstall"

@router.get("/installed")
def get_installed_plugins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_plugins = db.query(UserPlugin).filter(UserPlugin.user_id == current_user.id).all()
    if not user_plugins:
        # Initialize default plugins for user in database
        for pid in DEFAULT_PLUGINS:
            db.add(UserPlugin(user_id=current_user.id, plugin_id=pid))
        try:
            db.commit()
            user_plugins = db.query(UserPlugin).filter(UserPlugin.user_id == current_user.id).all()
        except Exception:
            db.rollback()
            return {"installed_plugin_ids": DEFAULT_PLUGINS}

    installed_ids = [p.plugin_id for p in user_plugins]
    return {"installed_plugin_ids": installed_ids}

@router.post("/toggle")
def toggle_plugin(
    req: TogglePluginRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(UserPlugin).filter(
        UserPlugin.user_id == current_user.id,
        UserPlugin.plugin_id == req.plugin_id
    ).first()

    if req.action == "install":
        if not existing:
            new_p = UserPlugin(user_id=current_user.id, plugin_id=req.plugin_id)
            db.add(new_p)
            db.commit()
        is_installed = True
    else:
        if existing:
            db.delete(existing)
            db.commit()
        is_installed = False

    total_count = db.query(UserPlugin).filter(UserPlugin.user_id == current_user.id).count()

    return {
        "success": True,
        "plugin_id": req.plugin_id,
        "is_installed": is_installed,
        "installed_count": total_count
    }
