"""
Phase 3 - Query API

Read-only API for Phase 3 data (profiles, baselines, drift records).
All endpoints are GET-only - no mutations.

Constraints:
- Read-only access
- No behavior modification
- Observational semantics only
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from backend.baselines import BehaviorBaselineDB
from backend.database import get_db
from backend.drift_engine import BehaviorDriftDB, BehaviorProfileDB


# ============================================================================
# Response Models (Pydantic)
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
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    description: Optional[str]
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
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class DriftTimelinePoint(BaseModel):
    """Single point in drift timeline."""

    timestamp: datetime
    metric: str
    value: float
    drift_detected: bool
    drift_id: Optional[UUID]


class DriftTimelineResponse(BaseModel):
    """Response model for drift timeline visualization."""

    agent_id: str
    agent_version: str
    environment: str
    timeline: List[DriftTimelinePoint]


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/v1/phase3", tags=["Phase 3 - Drift Detection"])


# ============================================================================
# Behavior Profile Endpoints
# ============================================================================

@router.get("/profiles", response_model=List[BehaviorProfileResponse])
async def list_profiles(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    agent_version: Optional[str] = Query(None, description="Filter by agent version"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
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


@router.get("/profiles/{profile_id}", response_model=BehaviorProfileResponse)
async def get_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get specific behavior profile by ID.
    """
    profile = db.query(BehaviorProfileDB).filter(
        BehaviorProfileDB.profile_id == profile_id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")

    return profile


# ============================================================================
# Behavior Baseline Endpoints
# ============================================================================

@router.get("/baselines", response_model=List[BehaviorBaselineResponse])
async def list_baselines(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    agent_version: Optional[str] = Query(None, description="Filter by agent version"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    baseline_type: Optional[str] = Query(None, description="Filter by baseline type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
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


@router.get("/baselines/{baseline_id}", response_model=BehaviorBaselineResponse)
async def get_baseline(
    baseline_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get specific behavior baseline by ID.
    """
    baseline = db.query(BehaviorBaselineDB).filter(
        BehaviorBaselineDB.baseline_id == baseline_id
    ).first()

    if not baseline:
        raise HTTPException(status_code=404, detail=f"Baseline {baseline_id} not found")

    return baseline


# ============================================================================
# Behavior Drift Endpoints
# ============================================================================

@router.get("/drift", response_model=List[BehaviorDriftResponse])
async def list_drift(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    agent_version: Optional[str] = Query(None, description="Filter by agent version"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    drift_type: Optional[str] = Query(None, description="Filter by drift type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
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


@router.get("/drift/timeline", response_model=DriftTimelineResponse)
async def drift_timeline(
    agent_id: str = Query(..., description="Agent ID (required)"),
    agent_version: Optional[str] = Query(None, description="Filter by agent version"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    start_date: Optional[datetime] = Query(None, description="Start of timeline"),
    end_date: Optional[datetime] = Query(None, description="End of timeline"),
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


# ============================================================================
# Summary/Stats Endpoints
# ============================================================================

class DriftSummary(BaseModel):
    """Summary statistics for drift detection."""

    total_drift_events: int
    unresolved_drift_events: int
    drift_by_severity: dict
    drift_by_type: dict
    agents_with_drift: int


@router.get("/drift/summary", response_model=DriftSummary)
async def drift_summary(
    environment: Optional[str] = Query(None, description="Filter by environment"),
    days: int = Query(7, ge=1, le=365, description="Number of days to summarize"),
    db: Session = Depends(get_db),
):
    """
    Get summary statistics for drift detection.

    Provides high-level overview of drift across all agents.
    """
    from datetime import timedelta

    cutoff_date = datetime.utcnow() - timedelta(days=days)

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
    unique_agents = len(set(d.agent_id for d in all_drift))

    return DriftSummary(
        total_drift_events=total_drift,
        unresolved_drift_events=unresolved,
        drift_by_severity=by_severity,
        drift_by_type=by_type,
        agents_with_drift=unique_agents,
    )


@router.get("/drift/{drift_id}", response_model=BehaviorDriftResponse)
async def get_drift(
    drift_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get specific drift event by ID.
    """
    drift = db.query(BehaviorDriftDB).filter(
        BehaviorDriftDB.drift_id == drift_id
    ).first()

    if not drift:
        raise HTTPException(status_code=404, detail=f"Drift {drift_id} not found")

    return drift
