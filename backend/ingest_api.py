"""
AgentTracer Platform - Ingest API

This module implements the write-only ingest API for Phase-1.

Design Principles:
1. Idempotent ingestion via run_id
2. Strict schema validation (reject invalid data)
3. Privacy enforcement (no prompts/responses)
4. Fast writes (<200ms p99)
5. Observable (logs + metrics)

Endpoints:
- POST /v1/runs: Ingest a complete agent run
"""

import logging
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.models import (
    AgentDecisionDB,
    AgentFailureDB,
    AgentQualitySignalDB,
    AgentRunCreate,
    AgentRunDB,
    AgentRunResponse,
    AgentStepDB,
    Base,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="AgentTracer Platform - Ingest API",
    description="Phase-1 write-only API for agent telemetry ingestion",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Database Configuration
# ============================================================================

# Read DATABASE_URL from environment variable, fallback to localhost for local dev
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/agent_observability")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


# ============================================================================
# Metrics & Observability
# ============================================================================

# Simple in-memory metrics (Phase-1)
# TODO: Replace with Prometheus/StatsD in production
metrics = {
    "runs_ingested_total": 0,
    "runs_failed_total": 0,
    "runs_duplicate_total": 0,
}


def increment_metric(metric_name: str):
    """Increment a metric counter"""
    if metric_name in metrics:
        metrics[metric_name] += 1


# ============================================================================
# API Endpoints
# ============================================================================


@app.post(
    "/v1/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest agent run telemetry",
    description="""
    Ingest a complete agent run with ordered steps and optional failure.

    **Phase-1 Requirements:**
    - Steps must be sequentially ordered (seq: 0, 1, 2, ...)
    - Failed runs must include a failure object
    - No prompts, responses, or PII allowed in metadata
    - Idempotent via run_id (duplicate runs return 200 OK)

    **Privacy Enforcement:**
    This endpoint validates that metadata contains no sensitive data.
    Requests with prompts, responses, or PII will be rejected.
    """,
)
async def ingest_run(
    run: AgentRunCreate,
    db: Session = Depends(get_db),
) -> AgentRunResponse:
    """
    Ingest a complete agent run.

    This endpoint enforces Phase-1 privacy and structural constraints:
    - Validates step sequencing
    - Ensures failure classification for failed runs
    - Rejects sensitive data in metadata

    Args:
        run: Validated agent run data
        db: Database session

    Returns:
        AgentRunResponse: Created run with steps and failures

    Raises:
        HTTPException 400: Invalid data or privacy violation
        HTTPException 409: Duplicate run_id (idempotency)
        HTTPException 500: Database error
    """
    try:
        # Check for duplicate run_id (idempotency)
        existing_run = db.query(AgentRunDB).filter(AgentRunDB.run_id == run.run_id).first()
        if existing_run:
            logger.info(f"Duplicate run_id {run.run_id} - returning existing run")
            increment_metric("runs_duplicate_total")
            return AgentRunResponse.model_validate(existing_run)

        # Create run record
        db_run = AgentRunDB(
            run_id=run.run_id,
            agent_id=run.agent_id,
            agent_version=run.agent_version,
            environment=run.environment,
            status=run.status,
            started_at=run.started_at,
            ended_at=run.ended_at,
        )
        db.add(db_run)

        # Flush to ensure run_id exists before adding related records
        # This is critical for Phase 2 foreign key constraints
        db.flush()

        # Create step records
        for step in run.steps:
            db_step = AgentStepDB(
                step_id=step.step_id,
                run_id=run.run_id,
                seq=step.seq,
                step_type=step.step_type,
                name=step.name,
                latency_ms=step.latency_ms,
                started_at=step.started_at,
                ended_at=step.ended_at,
                step_metadata=step.metadata,
            )
            db.add(db_step)

        # Flush to ensure step_ids exist before adding decisions/failures that reference them
        # This is critical for Phase 2 foreign key constraints on step_id
        db.flush()

        # Create failure record if present
        if run.failure:
            db_failure = AgentFailureDB(
                run_id=run.run_id,
                step_id=run.failure.step_id,
                failure_type=run.failure.failure_type,
                failure_code=run.failure.failure_code,
                message=run.failure.message,
            )
            db.add(db_failure)

        # Phase 2: Create decision records if present (optional)
        if run.decisions:
            for decision in run.decisions:
                # Merge candidates into metadata if provided
                decision_metadata = decision.metadata.copy()
                if decision.candidates:
                    decision_metadata["candidates"] = decision.candidates

                db_decision = AgentDecisionDB(
                    decision_id=decision.decision_id,
                    run_id=run.run_id,
                    step_id=decision.step_id,
                    decision_type=decision.decision_type,
                    selected=decision.selected,
                    reason_code=decision.reason_code,
                    confidence=decision.confidence,
                    decision_metadata=decision_metadata,
                )
                db.add(db_decision)

        # Phase 2: Create quality signal records if present (optional)
        if run.quality_signals:
            for signal in run.quality_signals:
                db_signal = AgentQualitySignalDB(
                    signal_id=signal.signal_id,
                    run_id=run.run_id,
                    step_id=signal.step_id,
                    signal_type=signal.signal_type,
                    signal_code=signal.signal_code,
                    value=signal.value,
                    weight=signal.weight,
                    signal_metadata=signal.metadata,
                )
                db.add(db_signal)

        # Commit transaction
        db.commit()
        db.refresh(db_run)

        # Update metrics
        increment_metric("runs_ingested_total")

        logger.info(
            f"Ingested run {run.run_id} for agent {run.agent_id} "
            f"with {len(run.steps)} steps (status: {run.status})"
            + (f", {len(run.decisions or [])} decisions" if run.decisions else "")
            + (f", {len(run.quality_signals or [])} signals" if run.quality_signals else "")
        )

        return AgentRunResponse.model_validate(db_run)

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Data integrity violation: {str(e)}",
        )

    except Exception as e:
        db.rollback()
        increment_metric("runs_failed_total")
        logger.error(f"Failed to ingest run: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest run: {str(e)}",
        )


@app.get(
    "/health",
    summary="Health check",
    description="Check if the ingest API is healthy and can connect to the database",
)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.

    Returns:
        dict: Health status
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "ingest-api",
            "version": "0.1.0",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        )


@app.get(
    "/metrics",
    summary="Internal metrics",
    description="Get internal metrics for observability (Phase-1 simple counters)",
)
async def get_metrics():
    """
    Get internal metrics.

    Phase-1 uses simple in-memory counters.
    Future: Integrate with Prometheus/StatsD.

    Returns:
        dict: Metric counters
    """
    return {
        "metrics": metrics,
        "note": "Phase-1 simple counters - will be replaced with proper metrics in production",
    }


# ============================================================================
# Startup/Shutdown Events
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Starting Ingest API...")
    init_db()
    logger.info("Ingest API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Ingest API...")


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with logging"""
    logger.warning(
        f"HTTP {exc.status_code} for {request.method} {request.url.path}: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn

    # For local development
    uvicorn.run(
        "backend.ingest_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
