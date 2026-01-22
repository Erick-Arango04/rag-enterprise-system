from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config.settings import get_settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""

    #Writing: MUST use global keyword
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url)

    #Reading: No global needed
    return _engine


def get_session_local():
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db():
    """Dependency generator for FastAPI injection."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
