"""
Centralized database configuration for all APIs
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.config.settings import settings

# Create database engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency for database sessions.
    Use with FastAPI Depends() to get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Called on application startup.
    """
    from server.models.database import Base

    Base.metadata.create_all(bind=engine)


def close_db():
    """
    Close database connections.
    Called on application shutdown.
    """
    engine.dispose()
