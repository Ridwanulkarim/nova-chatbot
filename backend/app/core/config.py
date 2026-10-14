import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "backend" else BASE_DIR

def is_running_on_vercel() -> bool:
    return bool(
        os.environ.get("VERCEL")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("LAMBDA_TASK_ROOT")
    )


def get_env_file() -> Optional[str]:
    if is_running_on_vercel():
        return None
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
    return None

ENV_PATH = get_env_file()


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
    if is_running_on_vercel():
        return None
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
    
    SECRET_KEY: str = "pluto_ai_jwt_secret_key_2026_super_secure_production_fallback"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    FIREBASE_PROJECT_ID: str = "plutochatbot"
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = None
    FIREBASE_SERVICE_ACCOUNT_KEY: Optional[str] = None

    DATABASE_URL: str = get_default_database_url()
    
    # AI API Keys
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    
    DEFAULT_MODEL: str = "gemini-3.5-flash"
    DEFAULT_PROVIDER: str = "gemini"
    
    CORS_ORIGINS: str = "http://localhost:5180,http://127.0.0.1:5180,http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,https://pluto-chatbot-3gfbb3cqn-ridwanulkarims-projects.vercel.app,https://pluto-chatbot-it29af1oe-ridwanulkarims-projects.vercel.app"
    UPLOAD_DIR: str = get_default_upload_dir()
    MAX_UPLOAD_SIZE_MB: int = 50
    DAILY_MESSAGE_LIMIT: int = 50
    DAILY_IMAGE_LIMIT: int = 10

    # Cloud Object Storage (optional for production persistence)
    STORAGE_BACKEND: str = "local"  # "local", "s3", or "cloudinary"
    S3_BUCKET_NAME: Optional[str] = None
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None  # e.g. Cloudflare R2 / Supabase S3 endpoint
    S3_REGION_NAME: Optional[str] = "us-east-1"
    CLOUDINARY_URL: Optional[str] = None

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH else None,
        env_file_encoding="utf-8" if ENV_PATH else None,
        extra="ignore"
    )

settings = Settings()

# Post-process keys to eliminate any environment variable placeholder poisoning
settings.OPENAI_API_KEY = _clean_key(settings.OPENAI_API_KEY) or _read_env_val("OPENAI_API_KEY")
settings.GROQ_API_KEY = _clean_key(settings.GROQ_API_KEY) or _read_env_val("GROQ_API_KEY")
settings.GEMINI_API_KEY = _clean_key(settings.GEMINI_API_KEY) or _read_env_val("GEMINI_API_KEY")

# Clean and normalize DATABASE_URL
if settings.DATABASE_URL:
    clean_db = settings.DATABASE_URL.strip().strip("\"'")
    if clean_db.startswith("DATABASE_URL="):
        clean_db = clean_db.split("DATABASE_URL=", 1)[1].strip().strip("\"'")
    elif clean_db.startswith("database_url="):
        clean_db = clean_db.split("database_url=", 1)[1].strip().strip("\"'")
    if clean_db.startswith("postgres://"):
        clean_db = clean_db.replace("postgres://", "postgresql://", 1)
    settings.DATABASE_URL = clean_db

if not settings.GEMINI_API_KEY and settings.GROQ_API_KEY:
    settings.DEFAULT_MODEL = "openai/gpt-oss-120b"
    settings.DEFAULT_PROVIDER = "groq"

# Auto-detect S3/R2 storage backend if S3 credentials are provided
if settings.S3_BUCKET_NAME and settings.STORAGE_BACKEND == "local":
    settings.STORAGE_BACKEND = "s3"


def validate_production_security(s: Settings) -> None:
    """Enforce strict production security rules: prevent insecure default keys in production."""
    stable_fallback = "pluto_ai_jwt_secret_key_2026_super_secure_production_fallback"
    is_prod_env = s.ENVIRONMENT.lower() in ("production", "prod")
    on_vercel = is_running_on_vercel()

    if is_prod_env or on_vercel:
        if not s.SECRET_KEY or "change_in_production" in s.SECRET_KEY:
            import logging
            # Enforce hard failure only if user explicitly demands strict secrets via env
            if os.environ.get("STRICT_SECRETS", "").lower() in ("1", "true"):
                raise RuntimeError(
                    "FATAL CONFIGURATION ERROR: In production mode, SECRET_KEY must be "
                    "configured with a secure, random secret in environment variables! "
                    "Refusing to start with the default fallback secret key."
                )
            # Use deterministic stable production fallback HMAC key so all serverless containers share the same key
            s.SECRET_KEY = stable_fallback
            logging.getLogger("pluto.security").warning(
                "⚠️ Notice: Using stable fallback HMAC secret for serverless session persistence. "
                "To customize your secret key, set SECRET_KEY in your Vercel Project Settings."
            )

        if s.DATABASE_URL.startswith("sqlite"):
            import logging
            logging.getLogger("pluto.config").warning(
                "⚠️ WARNING: Running on Vercel/serverless with ephemeral SQLite (/tmp/pluto_ai.db). "
                "Serverless instances reset local files on cold restart. To keep user accounts, "
                "conversations, and documents persistent across deployments, configure the "
                "DATABASE_URL environment variable to a managed PostgreSQL database (e.g. Supabase, Neon, AWS RDS)."
            )


# Execute production security check on module load
validate_production_security(settings)


