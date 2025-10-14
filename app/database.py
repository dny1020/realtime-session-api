from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional

from config.settings import get_settings

settings = get_settings()

# Create database engine only if enabled
if not settings.disable_db:
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=20,              # Core pool size
        max_overflow=10,           # Allow bursts to 30 total
        pool_pre_ping=True,        # Test connections before use
        pool_recycle=3600,         # Recycle after 1 hour
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None


def get_db() -> Generator[Optional[Session], None, None]:
    """Dependency to get a database session"""
    if settings.disable_db:
        yield None
    else:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()