from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings, is_running_on_vercel
from app.database.connection import configure_database_connection

# Configure database URL, driver arguments (e.g. SSL for pg8000), and serverless pool options
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

def get_db():
    """FastAPI database session dependency with lifecycle management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
