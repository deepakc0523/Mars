"""
Database engine, session management, and startup initialization for MARS.
"""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base


def _ensure_sqlite_dir(database_url: str) -> None:
    """Ensure the directory for SQLite file exists if using sqlite:/// file path."""
    if database_url.startswith("sqlite:///"):
        db_path_str = database_url.replace("sqlite:///", "")
        # Filter out :memory: or query params
        if db_path_str and not db_path_str.startswith(":memory:"):
            clean_path = db_path_str.split("?")[0]
            db_path = Path(clean_path).resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)


settings = get_settings()
_ensure_sqlite_dir(settings.database_url)

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Initialize database schema.

    Creates target parent directories and all tables defined in models.
    Called automatically on FastAPI startup.
    """
    # Import all models to register with Base.metadata
    import app.db.models  # noqa: F401

    _ensure_sqlite_dir(get_settings().database_url)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a transactional database session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
