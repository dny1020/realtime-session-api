from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Optional

from config.settings import get_settings
# from app.models import Base  # not needed here; migrations handle schema

settings = get_settings()

# Make engine database only if DB is enabled
if not settings.disable_db:
    engine = create_engine(
        settings.database_url,
        echo=settings.debug  # Show SQL queries in debug mode
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None  # type: ignore
    SessionLocal = None  # type: ignore


def get_db() -> Generator[Optional[Session], None, None]:
    """
    Dependency to get a database session
    
    Yields:
        Session: SQLAlchemy session
    """
    if settings.disable_db:
        # Minimal mode: do not open connection
        yield None
    else:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()