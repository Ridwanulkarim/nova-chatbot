"""
Top-level entrypoint for Vercel Python runtime service.
Exposes FastAPI 'app' instance from app.main.
"""
from app.main import app

__all__ = ["app"]
