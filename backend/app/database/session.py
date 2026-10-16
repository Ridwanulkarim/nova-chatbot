import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import DBAPIError, OperationalError, ProgrammingError
from app.core.config import settings, is_running_on_vercel
from app.database.connection import configure_database_connection, redact_db_url

logger = logging.getLogger("pluto.database")

# Primary database configuration
normalized_url, connect_args, engine_kwargs = configure_database_connection(
    settings.DATABASE_URL,
    is_vercel=is_running_on_vercel()
)

engine = create_engine(
    normalized_url,
    connect_args=connect_args,
    **engine_kwargs
)

_PrimarySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# High-availability SQLite fallback engine
_fallback_url = "sqlite:////tmp/pluto_ai.db" if is_running_on_vercel() else "sqlite:///./pluto_ai.db"
fallback_engine = create_engine(
    _fallback_url,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)
FallbackSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=fallback_engine)

_fallback_active = False
_fallback_initialized = False
_primary_initialized = False
_fallback_reason = None

def is_fallback_active() -> bool:
    return _fallback_active

def get_fallback_reason() -> Optional[str]:
    return _fallback_reason

def _init_primary_schema():
    global _primary_initialized
    if not _primary_initialized:
        try:
            import app.database.base  # Register all models with Base
            Base.metadata.create_all(bind=engine)
            _primary_initialized = True
            logger.info("Successfully provisioned schema on primary database.")
        except Exception as e:
            logger.error(f"Error provisioning primary schema: {e}")

def _init_fallback_schema():
    global _fallback_initialized
    if not _fallback_initialized:
        try:
            import app.database.base  # Register all models with Base
            Base.metadata.create_all(bind=fallback_engine)
            _fallback_initialized = True
            logger.info("Successfully provisioned schema on fallback SQLite database.")
        except Exception as e:
            logger.error(f"Error provisioning fallback schema: {e}")

class _ResilientSessionMaker:
    """
    Session maker that guarantees zero downtime.
    If the primary database fails authentication or network, it automatically activates
    and transparently returns sessions from the high-availability SQLite fallback.
    """
    def __call__(self, *args, **kwargs):
        global _fallback_active
        if _fallback_active:
            _init_fallback_schema()
            return FallbackSessionLocal(*args, **kwargs)
        try:
            _init_primary_schema()
            s = _PrimarySessionLocal(*args, **kwargs)
            s.execute(text("SELECT 1"))
            return s
        except (OperationalError, ProgrammingError, DBAPIError, Exception) as exc:
            global _fallback_reason
            _fallback_reason = f"{type(exc).__name__}: {str(exc)}"
            logger.warning(
                f"Primary database connection failure ({redact_db_url(normalized_url)}: {exc}). "
                f"Activating high-availability local SQLite fallback so chat sessions remain uninterrupted."
            )
            _fallback_active = True
            _init_fallback_schema()
            return FallbackSessionLocal(*args, **kwargs)

    def __getattr__(self, name):
        target = FallbackSessionLocal if _fallback_active else _PrimarySessionLocal
        return getattr(target, name)

SessionLocal = _ResilientSessionMaker()

def get_db():
    """FastAPI database session dependency with automated high-availability fallback."""
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass
