from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.session import get_db
from app.ai.provider_factory import ai_factory
from app.core.config import settings

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    available_models = ai_factory.list_available_models()
    return {
        "status": "online",
        "app_name": "Nova AI",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "ai_providers_ready": ai_factory.has_any_provider(),
        "available_model_count": len(available_models),
        "available_models": [m["id"] for m in available_models],
    }
