"""
AgentTracer Platform - Ingest API

This module implements the write-only ingest API for agent telemetry.

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

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.config.settings import settings
from server.database import close_db, get_db, init_db
from server.middleware.setup import setup_cors, setup_error_handlers
from server.models.database import (
    AgentDecisionDB,
    AgentFailureDB,
    AgentQualitySignalDB,
    AgentRunCreate,
    AgentRunDB,
    AgentRunResponse,
    AgentStepDB,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI Application
app = FastAPI(
    title=f"{settings.APP_NAME} - Ingest API",
    description="Write-only API for agent telemetry ingestion",
    version=settings.VERSION,
)

# Setup middleware
setup_cors(app)
setup_error_handlers(app)


# Metrics & Observability

# Simple in-memory metrics for development
# In production, replace with Prometheus/StatsD
metrics = {
    "runs_ingested_total": 0,
    "runs_failed_total": 0,
    "runs_duplicate_total": 0,
}


def increment_metric(metric_name: str):
    """Increment a metric counter"""
    if metric_name in metrics:
        metrics[metric_name] += 1


# Helper Functions for Ingest Operations


def _check_duplicate_run(db: Session, run_id) -> AgentRunResponse | None:
    """
    Check if run already exists and return it if found (idempotency).

    Args:
        db: Database session
        run_id: Run identifier to check

    Returns:
        AgentRunResponse if duplicate found, None otherwise
    """
    existing_run = db.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()
    if existing_run:
        logger.info(f"Duplicate run_id {run_id} - returning existing run")
        increment_metric("runs_duplicate_total")
        return AgentRunResponse.model_validate(existing_run)
    return None


def _create_run_record(db: Session, run: AgentRunCreate) -> AgentRunDB:
    """
    Create and return the main AgentRun database record.

    Args:
        db: Database session
        run: Validated run data from request

    Returns:
        Created AgentRunDB instance
    """
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
    db.flush()  # Ensure run_id exists before adding related records
    return db_run


def _create_step_records(db: Session, run: AgentRunCreate) -> None:
    """
    Create all step records for the run.

    Args:
        db: Database session
        run: Validated run data containing steps
    """
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
    db.flush()  # Ensure step_ids exist for potential references


def _create_failure_record(db: Session, run: AgentRunCreate) -> None:
    """
    Create failure record if present in run data.

    Args:
        db: Database session
        run: Validated run data potentially containing failure
    """
    if run.failure:
        db_failure = AgentFailureDB(
            run_id=run.run_id,
            step_id=run.failure.step_id,
            failure_type=run.failure.failure_type,
            failure_code=run.failure.failure_code,
            message=run.failure.message,
        )
        db.add(db_failure)


def _create_decision_records(db: Session, run: AgentRunCreate) -> None:
    """
    Create decision records if present (optional behavioral tracking).

    Args:
        db: Database session
        run: Validated run data potentially containing decisions
    """
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


def _create_quality_signal_records(db: Session, run: AgentRunCreate) -> None:
    """
    Create quality signal records if present (optional behavioral tracking).

    Args:
        db: Database session
        run: Validated run data potentially containing quality signals
    """
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


# API Endpoints


@app.post(
    "/v1/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest agent run telemetry",
    description="""
    Ingest a complete agent run with ordered steps and optional failure.

    **Requirements:**
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

    This endpoint enforces privacy and structural constraints:
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
        # Check for duplicate run (idempotency)
        duplicate_response = _check_duplicate_run(db, run.run_id)
        if duplicate_response:
            return duplicate_response

        # Create run and related records
        db_run = _create_run_record(db, run)
        _create_step_records(db, run)
        _create_failure_record(db, run)
        _create_decision_records(db, run)
        _create_quality_signal_records(db, run)

        # Commit transaction
        db.commit()
        db.refresh(db_run)

        # Update metrics and log success
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
        ) from e

    except Exception as e:
        db.rollback()
        increment_metric("runs_failed_total")
        logger.error(f"Failed to ingest run: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest run: {str(e)}",
        ) from e


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
        ) from e


@app.get(
    "/metrics",
    summary="Internal metrics",
    description="Get internal metrics for observability",
)
async def get_metrics():
    """
    Get internal metrics.

    Uses simple in-memory counters for development.
    In production, integrate with Prometheus/StatsD.

    Returns:
        dict: Metric counters
    """
    return {
        "metrics": metrics,
        "note": "Simple in-memory counters - will be replaced with proper metrics in production",
    }


# Startup/Shutdown Events


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
    close_db()
    logger.info("Ingest API shut down successfully")


if __name__ == "__main__":
    import uvicorn

    # For local development
    uvicorn.run(
        "server.api.ingest:app",
        host="0.0.0.0",
        port=settings.INGEST_API_PORT,
        reload=True,
        log_level="info",
    )
