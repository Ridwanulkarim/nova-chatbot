import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "backend" else BASE_DIR

def get_env_file():
    candidates = [
        PROJECT_ROOT / ".env",
        BASE_DIR / ".env",
        PROJECT_ROOT / "nova_ai.env",
        BASE_DIR / "nova_ai.env"
    ]
    for p in candidates:
        try:
            if p.exists() and os.access(str(p), os.R_OK):
                with open(str(p), "r") as f:
                    f.read(1)
                return str(p)
        except Exception:
            continue
    return str(PROJECT_ROOT / ".env")

ENV_PATH = get_env_file()


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    DEBUG: bool = True
    
    SECRET_KEY: str = "nova_ai_default_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    DATABASE_URL: str = "sqlite:///./nova_ai.db"
    
    # AI API Keys
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    DEFAULT_MODEL: str = "gpt-4o-mini"
    DEFAULT_PROVIDER: str = "openai"
    
    CORS_ORIGINS: str = "http://localhost:5180,http://127.0.0.1:5180,http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    DAILY_MESSAGE_LIMIT: int = 50
    DAILY_IMAGE_LIMIT: int = 10

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
