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
        PROJECT_ROOT / "pluto_ai.env",
        BASE_DIR / "pluto_ai.env",
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


def is_running_on_vercel() -> bool:
    return bool(
        os.environ.get("VERCEL")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("LAMBDA_TASK_ROOT")
    )


def get_default_upload_dir() -> str:
    if is_running_on_vercel():
        return "/tmp/uploads"
    try:
        local_dir = "./uploads"
        os.makedirs(local_dir, exist_ok=True)
        return local_dir
    except Exception:
        return "/tmp/uploads"


def get_default_database_url() -> str:
    if is_running_on_vercel():
        return "sqlite:////tmp/pluto_ai.db"
    try:
        test_file = "./.write_test_db"
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return "sqlite:///./pluto_ai.db"
    except Exception:
        return "sqlite:////tmp/pluto_ai.db"


def _clean_key(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    val = val.strip().strip("\"'")
    if not val or val.startswith("your_") or "placeholder" in val.lower() or val in ["none", "null"]:
        return None
    return val


def _read_env_val(key_name: str) -> Optional[str]:
    # Check candidate env files directly if os.environ has placeholder or missing
    candidates = [
        ENV_PATH,
        PROJECT_ROOT / ".env",
        BASE_DIR / ".env",
        PROJECT_ROOT / "pluto_ai.env",
        BASE_DIR / "pluto_ai.env",
        PROJECT_ROOT / "nova_ai.env",
        BASE_DIR / "nova_ai.env",
    ]
    for p in candidates:
        try:
            if Path(p).exists():
                with open(str(p), "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith(f"{key_name}="):
                            val = line.split("=", 1)[1].strip()
                            clean = _clean_key(val)
                            if clean:
                                return clean
        except Exception:
            continue
    return None


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    DEBUG: bool = True
    
    SECRET_KEY: str = "pluto_ai_default_secret_key_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    DATABASE_URL: str = get_default_database_url()
    
    # AI API Keys
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    DEFAULT_MODEL: str = "gemini-3.5-flash"
    DEFAULT_PROVIDER: str = "gemini"
    
    CORS_ORIGINS: str = "http://localhost:5180,http://127.0.0.1:5180,http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,https://pluto-chatbot-it29af1oe-ridwanulkarims-projects.vercel.app,https://pluto-chatbot.vercel.app"
    UPLOAD_DIR: str = get_default_upload_dir()
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

# Post-process keys to eliminate any environment variable placeholder poisoning
settings.OPENAI_API_KEY = _clean_key(settings.OPENAI_API_KEY) or _read_env_val("OPENAI_API_KEY")
settings.GROQ_API_KEY = _clean_key(settings.GROQ_API_KEY) or _read_env_val("GROQ_API_KEY")
settings.GEMINI_API_KEY = _clean_key(settings.GEMINI_API_KEY) or _read_env_val("GEMINI_API_KEY")

if not settings.GEMINI_API_KEY and settings.GROQ_API_KEY:
    settings.DEFAULT_MODEL = "openai/gpt-oss-120b"
    settings.DEFAULT_PROVIDER = "groq"


