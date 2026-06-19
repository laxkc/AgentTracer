"""
AgentTracer Platform - Query API

This module implements the read-only query API for agent telemetry.

Design Principles:
1. Read-only operations (no mutations)
2. Efficient queries with pagination
3. Filter by agent_id, version, status, time range
4. Aggregated statistics for UI

Endpoints:
- GET /v1/runs: List agent runs with filters
- GET /v1/runs/{run_id}: Get a specific run with steps and failures
- GET /v1/stats: Get aggregated statistics
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from server.config.settings import settings
from server.database import close_db, get_db, init_db
from server.middleware.setup import setup_cors, setup_error_handlers
from server.models.database import (
    AgentFailureDB,
    AgentFailureResponse,
    AgentRunDB,
    AgentRunResponse,
    AgentStepDB,
    AgentStepResponse,
    BehaviorBaselineDB,
    BehaviorDriftDB,
    BehaviorProfileDB,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI Application
app = FastAPI(
    title=f"{settings.APP_NAME} - Query API",
    description="Read-only API for querying agent telemetry and drift detection",
    version=settings.VERSION,
)

# Setup middleware
setup_cors(app)
setup_error_handlers(app)


# Response Models


class RunListResponse(BaseModel):
    """Response for listing runs with pagination"""

    runs: list[AgentRunResponse]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Aggregated statistics response"""

    total_runs: int
    total_failures: int
    success_rate: float
    avg_latency_ms: float
    failure_breakdown: dict
    step_type_breakdown: dict

    class Config:
        from_attributes = True


# API Endpoints


@app.get(
    "/v1/runs",
    response_model=list[AgentRunResponse],
    summary="List agent runs",
    description="""
    Query agent runs with optional filters.

    **Filters:**
    - agent_id: Filter by specific agent
    - agent_version: Filter by agent version
    - status: Filter by run status (success, failure, partial)
    - environment: Filter by environment (production, staging, etc.)
    - start_time: Filter runs started after this timestamp
    - end_time: Filter runs started before this timestamp

    **Pagination:**
    - page: Page number (default: 1)
    - page_size: Results per page (default: 20, max: 100)
    """,
)
async def list_runs(
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    agent_version: str | None = Query(None, description="Filter by agent version"),
    status: str | None = Query(None, description="Filter by status"),
    environment: str | None = Query(None, description="Filter by environment"),
    start_time: datetime | None = Query(None, description="Filter by start time (after)"),
    end_time: datetime | None = Query(None, description="Filter by start time (before)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db),
) -> list[AgentRunResponse]:
    """
    List agent runs with optional filters and pagination.

    Args:
        agent_id: Filter by agent ID
        agent_version: Filter by agent version
        status: Filter by run status
        environment: Filter by environment
        start_time: Filter runs started after this time
        end_time: Filter runs started before this time
        page: Page number (1-indexed)
        page_size: Results per page
        db: Database session

    Returns:
        List[AgentRunResponse]: List of runs
    """
    try:
        # Build query with filters
        query = db.query(AgentRunDB)

        if agent_id:
            query = query.filter(AgentRunDB.agent_id == agent_id)

        if agent_version:
            query = query.filter(AgentRunDB.agent_version == agent_version)

        if status:
            query = query.filter(AgentRunDB.status == status)

        if environment:
            query = query.filter(AgentRunDB.environment == environment)

        if start_time:
            query = query.filter(AgentRunDB.started_at >= start_time)

        if end_time:
            query = query.filter(AgentRunDB.started_at <= end_time)

        # Order by most recent first
        query = query.order_by(desc(AgentRunDB.started_at))

        # Apply pagination
        offset = (page - 1) * page_size
        runs = query.offset(offset).limit(page_size).all()

        logger.info(f"Retrieved {len(runs)} runs (page {page}, size {page_size})")

        return [AgentRunResponse.model_validate(run) for run in runs]

    except Exception as e:
        logger.error(f"Failed to list runs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list runs: {str(e)}",
        ) from e


@app.get(
    "/v1/runs/{run_id}",
    response_model=AgentRunResponse,
    summary="Get a specific run",
    description="""
    Retrieve a complete agent run by ID, including:
    - All ordered steps
    - Failure classification (if any)
    - Complete timeline reconstruction
    """,
)
async def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
) -> AgentRunResponse:
    """
    Get a specific agent run with all steps and failures.

    Args:
        run_id: Run UUID
        db: Database session

    Returns:
        AgentRunResponse: Complete run data

    Raises:
        HTTPException 404: Run not found
    """
    try:
        run = db.query(AgentRunDB).filter(AgentRunDB.run_id == run_id).first()

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run {run_id} not found",
            )

        logger.info(f"Retrieved run {run_id} with {len(run.steps)} steps")

        return AgentRunResponse.model_validate(run)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get run: {str(e)}",
        ) from e


@app.get(
    "/v1/runs/{run_id}/steps",
    response_model=list[AgentStepResponse],
    summary="Get steps for a run",
    description="Retrieve all ordered steps for a specific run",
)
async def get_run_steps(
    run_id: UUID,
    db: Session = Depends(get_db),
) -> list[AgentStepResponse]:
    """
    Get all steps for a specific run, ordered by sequence.

    Args:
        run_id: Run UUID
        db: Database session

    Returns:
        List[AgentStepResponse]: Ordered list of steps
    """
    try:
        steps = (
            db.query(AgentStepDB)
            .filter(AgentStepDB.run_id == run_id)
            .order_by(AgentStepDB.seq)
            .all()
        )

        if not steps:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No steps found for run {run_id}",
            )

        return [AgentStepResponse.model_validate(step) for step in steps]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get steps for run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get steps: {str(e)}",
        ) from e


@app.get(
    "/v1/runs/{run_id}/failures",
    response_model=list[AgentFailureResponse],
    summary="Get failures for a run",
    description="Retrieve all failures for a specific run",
)
async def get_run_failures(
    run_id: UUID,
    db: Session = Depends(get_db),
) -> list[AgentFailureResponse]:
    """
    Get all failures for a specific run.

    Args:
        run_id: Run UUID
        db: Database session

    Returns:
        List[AgentFailureResponse]: List of failures
    """
    try:
        failures = db.query(AgentFailureDB).filter(AgentFailureDB.run_id == run_id).all()

        return [AgentFailureResponse.model_validate(failure) for failure in failures]

    except Exception as e:
        logger.error(f"Failed to get failures for run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get failures: {str(e)}",
        ) from e


def _calculate_run_statistics(runs_query, db) -> tuple:
    """
    Calculate total runs, failures, and success rate.

    Args:
        runs_query: SQLAlchemy query for filtered runs
        db: Database session

    Returns:
        Tuple of (total_runs, total_failures, success_rate)
    """
    total_runs = runs_query.count()
    total_failures = runs_query.filter(AgentRunDB.status == "failure").count()
    success_rate = ((total_runs - total_failures) / total_runs * 100) if total_runs > 0 else 0.0
    return total_runs, total_failures, success_rate


def _calculate_average_latency(run_ids: list, db: Session) -> float:
    """
    Calculate average latency from steps.

    Args:
        run_ids: List of run IDs to calculate latency for
        db: Database session

    Returns:
        Average latency in milliseconds
    """
    if not run_ids:
        return 0.0

    avg_latency_result = (
        db.query(func.avg(AgentStepDB.latency_ms)).filter(AgentStepDB.run_id.in_(run_ids)).scalar()
    )
    return float(avg_latency_result) if avg_latency_result else 0.0


def _calculate_failure_breakdown(run_ids: list, db: Session) -> dict:
    """
    Calculate failure breakdown by type and code.

    Args:
        run_ids: List of run IDs to analyze
        db: Database session

    Returns:
        Dict mapping "failure_type/failure_code" to count
    """
    failures = (
        db.query(
            AgentFailureDB.failure_type,
            AgentFailureDB.failure_code,
            func.count(AgentFailureDB.failure_id).label("count"),
        )
        .filter(AgentFailureDB.run_id.in_(run_ids) if run_ids else False)
        .group_by(AgentFailureDB.failure_type, AgentFailureDB.failure_code)
        .all()
    )

    failure_breakdown = {}
    for failure_type, failure_code, count in failures:
        key = f"{failure_type}/{failure_code}"
        failure_breakdown[key] = count

    return failure_breakdown


def _calculate_step_breakdown(run_ids: list, db: Session) -> dict:
    """
    Calculate step type breakdown.

    Args:
        run_ids: List of run IDs to analyze
        db: Database session

    Returns:
        Dict mapping step_type to count
    """
    steps = (
        db.query(AgentStepDB.step_type, func.count(AgentStepDB.step_id).label("count"))
        .filter(AgentStepDB.run_id.in_(run_ids) if run_ids else False)
        .group_by(AgentStepDB.step_type)
        .all()
    )

    step_type_breakdown = {}
    for step_type, count in steps:
        step_type_breakdown[step_type] = count

    return step_type_breakdown


@app.get(
    "/v1/stats",
    summary="Get aggregated statistics",
    description="""
    Get aggregated statistics for agent runs:
    - Total runs and failures
    - Success rate
    - Average latency
    - Failure breakdown by type and code
    - Step type breakdown

    Optional filters by agent_id, version, environment, and time range.
    """,
)
async def get_stats(
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    agent_version: str | None = Query(None, description="Filter by agent version"),
    environment: str | None = Query(None, description="Filter by environment"),
    start_time: datetime | None = Query(None, description="Filter by start time (after)"),
    end_time: datetime | None = Query(None, description="Filter by start time (before)"),
    db: Session = Depends(get_db),
):
    """
    Get aggregated statistics for the UI.

    Args:
        agent_id: Optional filter by agent ID
        agent_version: Optional filter by agent version
        environment: Optional filter by environment
        start_time: Optional start time filter
        end_time: Optional end time filter
        db: Database session

    Returns:
        dict: Aggregated statistics
    """
    try:
        # Build base query
        runs_query = db.query(AgentRunDB)

        if agent_id:
            runs_query = runs_query.filter(AgentRunDB.agent_id == agent_id)
        if agent_version:
            runs_query = runs_query.filter(AgentRunDB.agent_version == agent_version)
        if environment:
            runs_query = runs_query.filter(AgentRunDB.environment == environment)
        if start_time:
            runs_query = runs_query.filter(AgentRunDB.started_at >= start_time)
        if end_time:
            runs_query = runs_query.filter(AgentRunDB.started_at <= end_time)

        # Calculate statistics
        total_runs, total_failures, success_rate = _calculate_run_statistics(runs_query, db)

        run_ids = [run.run_id for run in runs_query.all()]
        avg_latency = _calculate_average_latency(run_ids, db)
        failure_breakdown = _calculate_failure_breakdown(run_ids, db)
        step_type_breakdown = _calculate_step_breakdown(run_ids, db)

        return {
            "total_runs": total_runs,
            "total_failures": total_failures,
            "success_rate": round(success_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "failure_breakdown": failure_breakdown,
            "step_type_breakdown": step_type_breakdown,
        }

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}",
        ) from e


@app.get(
    "/health",
    summary="Health check",
    description="Check if the query API is healthy",
)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "query-api",
            "version": "0.1.0",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}",
        ) from e


# ============================================================================
# Drift Detection Endpoints
# ============================================================================


class BehaviorProfileResponse(BaseModel):
    """Response model for behavior profiles."""

    profile_id: UUID
    agent_id: str
    agent_version: str
    environment: str
    window_start: datetime
    window_end: datetime
    sample_size: int
    decision_distributions: dict
    signal_distributions: dict
    latency_stats: dict
    created_at: datetime

    class Config:
        from_attributes = True


class BehaviorBaselineResponse(BaseModel):
    """Response model for behavior baselines."""

    baseline_id: UUID
    profile_id: UUID
    agent_id: str
    agent_version: str
    environment: str
    baseline_type: str
    approved_by: str | None
    approved_at: datetime | None
    description: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BehaviorDriftResponse(BaseModel):
    """Response model for behavior drift events."""

    drift_id: UUID
    baseline_id: UUID
    agent_id: str
    agent_version: str
    environment: str
    drift_type: str
    metric: str
    baseline_value: float
    observed_value: float
    delta: float
    delta_percent: float
    significance: float
    test_method: str
    severity: str
    detected_at: datetime
    observation_window_start: datetime
    observation_window_end: datetime
    observation_sample_size: int
    resolved_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class DriftTimelinePoint(BaseModel):
    """Single point in drift timeline."""

    timestamp: datetime
    metric: str
    value: float
    drift_detected: bool
    drift_id: UUID | None


class DriftTimelineResponse(BaseModel):
    """Response model for drift timeline visualization."""

    agent_id: str
    agent_version: str
    environment: str
    timeline: list[DriftTimelinePoint]


class DriftSummary(BaseModel):
    """Summary statistics for drift detection."""

    total_drift_events: int
    unresolved_drift_events: int
    drift_by_severity: dict
    drift_by_type: dict
    agents_with_drift: int


@app.get(
    "/v1/drift/profiles", response_model=list[BehaviorProfileResponse], tags=["Drift Detection"]
)
async def list_profiles(
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    agent_version: str | None = Query(None, description="Filter by agent version"),
    environment: str | None = Query(None, description="Filter by environment"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """
    List behavior profiles with optional filtering.

    Profiles are statistical snapshots of agent behavior over time windows.
    """
    query = db.query(BehaviorProfileDB)

    # Apply filters
    if agent_id:
        query = query.filter(BehaviorProfileDB.agent_id == agent_id)
    if agent_version:
        query = query.filter(BehaviorProfileDB.agent_version == agent_version)
    if environment:
        query = query.filter(BehaviorProfileDB.environment == environment)

    # Order by created_at descending
    query = query.order_by(desc(BehaviorProfileDB.created_at))

    # Pagination
    query = query.limit(limit).offset(offset)

    profiles = query.all()
    return profiles


@app.get(
    "/v1/drift/profiles/{profile_id}",
    response_model=BehaviorProfileResponse,
    tags=["Drift Detection"],
)
async def get_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get specific behavior profile by ID.
    """
    profile = db.query(BehaviorProfileDB).filter(BehaviorProfileDB.profile_id == profile_id).first()

    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")

    return profile


@app.get(
    "/v1/drift/baselines", response_model=list[BehaviorBaselineResponse], tags=["Drift Detection"]
)
async def list_baselines(
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    agent_version: str | None = Query(None, description="Filter by agent version"),
    environment: str | None = Query(None, description="Filter by environment"),
    baseline_type: str | None = Query(None, description="Filter by baseline type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """
    List behavior baselines with optional filtering.

    Baselines are immutable snapshots of expected agent behavior.
    """
    query = db.query(BehaviorBaselineDB)

    # Apply filters
    if agent_id:
        query = query.filter(BehaviorBaselineDB.agent_id == agent_id)
    if agent_version:
        query = query.filter(BehaviorBaselineDB.agent_version == agent_version)
    if environment:
        query = query.filter(BehaviorBaselineDB.environment == environment)
    if baseline_type:
        query = query.filter(BehaviorBaselineDB.baseline_type == baseline_type)
    if is_active is not None:
        query = query.filter(BehaviorBaselineDB.is_active == is_active)

    # Order by created_at descending
    query = query.order_by(desc(BehaviorBaselineDB.created_at))

    # Pagination
    query = query.limit(limit).offset(offset)

    baselines = query.all()
    return baselines


@app.get(
    "/v1/drift/baselines/{baseline_id}",
    response_model=BehaviorBaselineResponse,
    tags=["Drift Detection"],
)
async def get_baseline(
    baseline_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get specific behavior baseline by ID.
    """
    baseline = (
        db.query(BehaviorBaselineDB).filter(BehaviorBaselineDB.baseline_id == baseline_id).first()
    )

    if not baseline:
        raise HTTPException(status_code=404, detail=f"Baseline {baseline_id} not found")

    return baseline


@app.get("/v1/drift", response_model=list[BehaviorDriftResponse], tags=["Drift Detection"])
async def list_drift(
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    agent_version: str | None = Query(None, description="Filter by agent version"),
    environment: str | None = Query(None, description="Filter by environment"),
    drift_type: str | None = Query(None, description="Filter by drift type"),
    severity: str | None = Query(None, description="Filter by severity"),
    resolved: bool | None = Query(None, description="Filter by resolution status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """
    List behavior drift events with optional filtering.

    Drift events are purely observational - they describe change, not quality.
    """
    query = db.query(BehaviorDriftDB)

    # Apply filters
    if agent_id:
        query = query.filter(BehaviorDriftDB.agent_id == agent_id)
    if agent_version:
        query = query.filter(BehaviorDriftDB.agent_version == agent_version)
    if environment:
        query = query.filter(BehaviorDriftDB.environment == environment)
    if drift_type:
        query = query.filter(BehaviorDriftDB.drift_type == drift_type)
    if severity:
        query = query.filter(BehaviorDriftDB.severity == severity)
    if resolved is not None:
        if resolved:
            query = query.filter(BehaviorDriftDB.resolved_at.isnot(None))
        else:
            query = query.filter(BehaviorDriftDB.resolved_at.is_(None))

    # Order by detected_at descending
    query = query.order_by(desc(BehaviorDriftDB.detected_at))

    # Pagination
    query = query.limit(limit).offset(offset)

    drift_events = query.all()
    return drift_events


@app.get("/v1/drift/timeline", response_model=DriftTimelineResponse, tags=["Drift Detection"])
async def drift_timeline(
    agent_id: str = Query(..., description="Agent ID (required)"),
    agent_version: str | None = Query(None, description="Filter by agent version"),
    environment: str | None = Query(None, description="Filter by environment"),
    start_date: datetime | None = Query(None, description="Start of timeline"),
    end_date: datetime | None = Query(None, description="End of timeline"),
    db: Session = Depends(get_db),
):
    """
    Get drift timeline for visualization.

    Returns time-series data suitable for charting drift over time.
    """
    query = db.query(BehaviorDriftDB).filter(BehaviorDriftDB.agent_id == agent_id)

    # Apply filters
    if agent_version:
        query = query.filter(BehaviorDriftDB.agent_version == agent_version)
    if environment:
        query = query.filter(BehaviorDriftDB.environment == environment)
    if start_date:
        query = query.filter(BehaviorDriftDB.detected_at >= start_date)
    if end_date:
        query = query.filter(BehaviorDriftDB.detected_at <= end_date)

    # Order by detected_at
    query = query.order_by(BehaviorDriftDB.detected_at)

    drift_events = query.all()

    # Build timeline points
    timeline = []
    for drift in drift_events:
        timeline.append(
            DriftTimelinePoint(
                timestamp=drift.detected_at,
                metric=drift.metric,
                value=drift.observed_value,
                drift_detected=True,
                drift_id=drift.drift_id,
            )
        )

    return DriftTimelineResponse(
        agent_id=agent_id,
        agent_version=agent_version or "all",
        environment=environment or "all",
        timeline=timeline,
    )


@app.get("/v1/drift/summary", response_model=DriftSummary, tags=["Drift Detection"])
async def drift_summary(
    environment: str | None = Query(None, description="Filter by environment"),
    days: int = Query(7, ge=1, le=365, description="Number of days to summarize"),
    db: Session = Depends(get_db),
):
    """
    Get summary statistics for drift detection.

    Provides high-level overview of drift across all agents.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(BehaviorDriftDB).filter(BehaviorDriftDB.detected_at >= cutoff_date)

    if environment:
        query = query.filter(BehaviorDriftDB.environment == environment)

    all_drift = query.all()

    # Count total drift events
    total_drift = len(all_drift)

    # Count unresolved
    unresolved = len([d for d in all_drift if d.resolved_at is None])

    # Group by severity
    by_severity = {}
    for drift in all_drift:
        by_severity[drift.severity] = by_severity.get(drift.severity, 0) + 1

    # Group by type
    by_type = {}
    for drift in all_drift:
        by_type[drift.drift_type] = by_type.get(drift.drift_type, 0) + 1

    # Count unique agents
    unique_agents = len({d.agent_id for d in all_drift})

    return DriftSummary(
        total_drift_events=total_drift,
        unresolved_drift_events=unresolved,
        drift_by_severity=by_severity,
        drift_by_type=by_type,
        agents_with_drift=unique_agents,
    )


@app.get("/v1/drift/{drift_id}", response_model=BehaviorDriftResponse, tags=["Drift Detection"])
async def get_drift(
    drift_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get specific drift event by ID.
    """
    drift = db.query(BehaviorDriftDB).filter(BehaviorDriftDB.drift_id == drift_id).first()

    if not drift:
        raise HTTPException(status_code=404, detail=f"Drift {drift_id} not found")

    return drift


@app.post(
    "/v1/drift/{drift_id}/resolve", response_model=BehaviorDriftResponse, tags=["Drift Detection"]
)
async def resolve_drift(
    drift_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Mark a drift event as resolved.

    This updates the resolved_at timestamp. Drift events are immutable otherwise.
    """
    drift = db.query(BehaviorDriftDB).filter(BehaviorDriftDB.drift_id == drift_id).first()

    if not drift:
        raise HTTPException(status_code=404, detail=f"Drift {drift_id} not found")

    if drift.resolved_at:
        raise HTTPException(status_code=400, detail="Drift event is already resolved")

    drift.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(drift)

    return drift


# Startup Event


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Starting Query API...")
    init_db()
    logger.info("Query API started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Query API...")
    close_db()
    logger.info("Query API shut down successfully")


if __name__ == "__main__":
    import uvicorn

    # For local development
    uvicorn.run(
        "server.api.query:app",
        host="0.0.0.0",
        port=settings.QUERY_API_PORT,
        reload=True,
        log_level="info",
    )
