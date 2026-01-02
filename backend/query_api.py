"""
AgentTracer Platform - Query API

This module implements the read-only query API for Phase-1.

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
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from backend.database import engine, get_db
from backend.models import (
    AgentDecisionDB,
    AgentDecisionResponse,
    AgentFailureDB,
    AgentFailureResponse,
    AgentQualitySignalDB,
    AgentQualitySignalResponse,
    AgentRunDB,
    AgentRunResponse,
    AgentStepDB,
    AgentStepResponse,
    Base,
)

# Import Phase 3 router
from backend.query_phase3 import router as phase3_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="AgentTracer Platform - Query API",
    description="Phase-1 read-only API for querying agent telemetry",
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

# Include Phase 3 router
app.include_router(phase3_router)


# ============================================================================
# Response Models
# ============================================================================


class RunListResponse(BaseModel):
    """Response for listing runs with pagination"""

    runs: List[AgentRunResponse]
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


# ============================================================================
# API Endpoints
# ============================================================================


@app.get(
    "/v1/runs",
    response_model=List[AgentRunResponse],
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
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    agent_version: Optional[str] = Query(None, description="Filter by agent version"),
    status: Optional[str] = Query(None, description="Filter by status"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time (after)"),
    end_time: Optional[datetime] = Query(None, description="Filter by start time (before)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db),
) -> List[AgentRunResponse]:
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
        )


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
        )


@app.get(
    "/v1/runs/{run_id}/steps",
    response_model=List[AgentStepResponse],
    summary="Get steps for a run",
    description="Retrieve all ordered steps for a specific run",
)
async def get_run_steps(
    run_id: UUID,
    db: Session = Depends(get_db),
) -> List[AgentStepResponse]:
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
        )


@app.get(
    "/v1/runs/{run_id}/failures",
    response_model=List[AgentFailureResponse],
    summary="Get failures for a run",
    description="Retrieve all failures for a specific run",
)
async def get_run_failures(
    run_id: UUID,
    db: Session = Depends(get_db),
) -> List[AgentFailureResponse]:
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
        )


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
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    agent_version: Optional[str] = Query(None, description="Filter by agent version"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    start_time: Optional[datetime] = Query(None, description="Filter by start time (after)"),
    end_time: Optional[datetime] = Query(None, description="Filter by start time (before)"),
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

        # Total runs
        total_runs = runs_query.count()

        # Total failures
        total_failures = runs_query.filter(AgentRunDB.status == "failure").count()

        # Success rate
        success_rate = (
            ((total_runs - total_failures) / total_runs * 100) if total_runs > 0 else 0.0
        )

        # Average latency (calculated from steps)
        run_ids = [run.run_id for run in runs_query.all()]
        avg_latency = 0.0
        if run_ids:
            avg_latency_result = (
                db.query(func.avg(AgentStepDB.latency_ms))
                .filter(AgentStepDB.run_id.in_(run_ids))
                .scalar()
            )
            avg_latency = float(avg_latency_result) if avg_latency_result else 0.0

        # Failure breakdown
        failure_breakdown = {}
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

        for failure_type, failure_code, count in failures:
            key = f"{failure_type}/{failure_code}"
            failure_breakdown[key] = count

        # Step type breakdown
        step_type_breakdown = {}
        steps = (
            db.query(
                AgentStepDB.step_type, func.count(AgentStepDB.step_id).label("count")
            )
            .filter(AgentStepDB.run_id.in_(run_ids) if run_ids else False)
            .group_by(AgentStepDB.step_type)
            .all()
        )

        for step_type, count in steps:
            step_type_breakdown[step_type] = count

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
        )


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
        )


# ============================================================================
# Startup Event
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Starting Query API...")
    logger.info("Query API started successfully")


if __name__ == "__main__":
    import uvicorn

    # For local development
    uvicorn.run(
        "backend.query_api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
