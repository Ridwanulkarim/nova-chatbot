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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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

def is_fallback_active() -> bool:
    return _fallback_active

def _init_fallback_schema():
    global _fallback_initialized
    if not _fallback_initialized:
        try:
            Base.metadata.create_all(bind=fallback_engine)
            _fallback_initialized = True
            logger.info("Successfully provisioned schema on fallback SQLite database.")
        except Exception as e:
            logger.error(f"Error provisioning fallback schema: {e}")

def get_db():
    """FastAPI database session dependency with automated high-availability fallback."""
    global _fallback_active

    if _fallback_active:
        _init_fallback_schema()
        db = FallbackSessionLocal()
        try:
            yield db
        finally:
            db.close()
        return

    # Attempt primary database session
    db = SessionLocal()
    try:
        # Pre-flight ping to detect credential or connection issues before route execution
        db.execute(text("SELECT 1"))
        yield db
    except (OperationalError, ProgrammingError, DBAPIError) as exc:
        db.rollback()
        db.close()
        logger.warning(
            f"Primary database connection failure ({redact_db_url(normalized_url)}: {exc}). "
            f"Activating high-availability local SQLite fallback so chat sessions remain uninterrupted."
        )
        _fallback_active = True
        _init_fallback_schema()
        fallback_db = FallbackSessionLocal()
        try:
            yield fallback_db
        finally:
            fallback_db.close()
    finally:
        try:
            db.close()
        except Exception:
            pass

