"""
Standalone Database Initialization Script.

Creates tables defined in SQLAlchemy models if they do not already exist.
This script is intentionally standalone and decoupled from the application startup/import
path to prevent concurrent DDL catalog lock contention on serverless cold starts.

Usage:
    # From project root:
    PYTHONPATH=backend python3 -m app.database.init_db

    # Or from backend/ directory:
    python3 -m app.database.init_db
"""
import sys
import logging
from app.database.session import engine, Base
import app.database.base  # Ensures all models are imported and registered with Base.metadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init_db")

def init_database() -> None:
    """Explicitly create all database tables using the configured engine."""
    logger.info("Initializing database schema...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    init_database()
