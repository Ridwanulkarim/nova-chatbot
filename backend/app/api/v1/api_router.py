from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, conversations, messages, files, settings, search, image, plugins

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(messages.router, prefix="/conversations", tags=["Messages"])
api_router.include_router(files.router, prefix="/files", tags=["Files & RAG"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings & Memory"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(image.router, prefix="/images", tags=["Image Generation"])
api_router.include_router(plugins.router, prefix="/plugins", tags=["Plugins & Skills"])
