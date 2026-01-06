"""
AgentTracer Platform - Database Configuration

Shared database session and dependency for all APIs.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Read DATABASE_URL from environment variable, fallback to localhost for local dev
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5433/agent_observability"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
