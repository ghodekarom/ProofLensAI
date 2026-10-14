"""SQLAlchemy engine, session management, and database health checks."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from prooflens.core.config import get_settings
from prooflens.core.logging import get_logger

logger = get_logger("prooflens.db.session")

_engine = None
_session_factory = None


def get_engine():
    """Returns singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=settings.DEBUG and not settings.is_production,
        )
    return _engine


def get_session_factory():
    """Returns singleton sessionmaker."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _session_factory


def get_db_session() -> Generator[Session]:
    """FastAPI dependency for obtaining a database session."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def check_database_readiness() -> dict[str, str]:
    """
    Checks database connection and verifies the pgvector extension is present.
    Returns dictionary with status flags or raises exception on failure.
    """
    engine = get_engine()
    results = {
        "database": "unknown",
        "vector_extension": "unknown",
    }

    with engine.connect() as conn:
        # Check basic connectivity
        conn.execute(text("SELECT 1"))
        results["database"] = "ok"

        # Check pgvector extension
        vector_check = conn.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        ).scalar()

        if vector_check:
            results["vector_extension"] = "ok"
        else:
            results["vector_extension"] = "missing"

    return results
