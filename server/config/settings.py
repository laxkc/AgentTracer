"""
Centralized configuration for AgentTracer platform APIs
"""

import os


class Settings:
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/agent_observability"
    )

    # API Ports
    INGEST_API_PORT: int = int(os.getenv("INGEST_API_PORT", "8000"))
    QUERY_API_PORT: int = int(os.getenv("QUERY_API_PORT", "8001"))

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
    ]

    # Application
    APP_NAME: str = "AgentTracer Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "").lower() == "true"

    # Database connection pool
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))


settings = Settings()
