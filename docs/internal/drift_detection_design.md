# Behavioral Drift Detection - Technical Design

## Current System Overview

The AgentTracer platform provides:

**Execution Observability:**
- AgentRun, AgentStep, AgentFailure
- Execution order, latency, retries, failures
- Framework-agnostic ingest (FastAPI + SDK)

**Decision & Quality Observability:**
- AgentDecision (explicit semantic decisions)
- AgentQualitySignal (observable outcome signals)
- Aggregation, correlation, version comparison
- Strict privacy boundaries (no prompts, no responses)

### Key Components

- Python SDK (agenttrace.py) - emits telemetry
- Ingest API - validates and persists data
- PostgreSQL - source of truth
- Query API - aggregation & correlation
- React UI - exploration and analysis

### Gap Addressed

Despite decision and quality observability, the system still requires manual inspection to detect:

- Silent regressions after deployment
- Gradual behavioral drift
- Decision distribution instability
- Signal degradation over time

There is **no operational signal** that tells humans when to look.

## Requirements

### Functional Requirements

1. **Behavioral Baseline Creation**
   - Generate stable statistical profiles from decision and quality data
   - Support version-based and time-window baselines

2. **Drift Detection**
   - Detect statistically significant changes in:
     - Decision distributions
     - Quality signal rates
     - Behavioral latency patterns
   - Compare live behavior against baselines

3. **Drift Recording**
   - Persist drift events with full explainability
   - Never overwrite historical baselines

4. **Alert Emission**
   - Emit non-blocking alerts for detected drift
   - Alerts must be human-readable and neutral

5. **UI Visualization**
   - Show baseline vs observed behavior
   - Visualize drift over time
   - Support drill-down to underlying runs

### Non-Functional Requirements

#### Performance

- Drift detection must run asynchronously
- Aggregation queries must not block ingest
- P95 drift computation < 5 seconds per agent

#### Scalability

- Support millions of runs
- Support thousands of agents
- Baselines must be reusable and cacheable

#### Observability

- Drift detection must emit its own metrics
- Drift detection must be auditable and explainable

#### Security

- Drift detection must not introduce any new sensitive data
- Baselines and drift events must contain no free text

## Design Decisions

### 1. Drift Detection via Distribution Comparison (not heuristics)

**Decision:** Use statistical comparison of distributions instead of rule-based heuristics.

**Rationale:**
- Heuristics do not generalize across domains
- Distribution deltas are domain-agnostic
- Supports version comparison naturally

**Trade-offs:**
- More compute than simple thresholds
- Requires minimum sample sizes

### 2. Baselines as First-Class Immutable Objects

**Decision:** Introduce explicit behavior_baselines instead of implicit "last version".

**Rationale:**
- Prevents silent baseline shifts
- Enables auditability
- Allows manual approval in regulated domains

**Alternatives Considered:**
- Rolling window comparison → rejected (unstable)
- Dynamic baselines → rejected (hard to reason about)

### 3. Alerts as Observational Signals (not actions)

**Decision:** Alerts are informational only.

**Rationale:**
- Avoids system becoming a controller
- Preserves human-in-the-loop responsibility
- Prevents unsafe automation

**Trade-offs:**
- Requires human interpretation
- No auto-mitigation

## Technical Design

### 1. Core Components

```python
class BehaviorProfileBuilder:
    """
    Builds statistical behavior profiles from decision and quality data.
    """
    def build_profile(self, agent_id: str, agent_version: str, window: TimeWindow) -> BehaviorProfile:
        pass

class DriftDetectionEngine:
    """
    Compares live behavior against baselines and detects drift.
    """
    def detect(self, baseline: BehaviorBaseline, observed: BehaviorProfile) -> list[BehaviorDrift]:
        pass

class AlertEmitter:
    """
    Emits human-readable alerts for detected drift.
    """
    def emit(self, drift: BehaviorDrift) -> None:
        pass
```

### 2. Data Models

```python
class BehaviorProfile(BaseModel):
    profile_id: UUID
    agent_id: str
    agent_version: str
    environment: str
    window_start: datetime
    window_end: datetime
    decision_distributions: dict
    signal_distributions: dict
    latency_stats: dict

class BehaviorBaseline(BaseModel):
    baseline_id: UUID
    profile_id: UUID
    baseline_type: Literal["version", "time_window", "manual"]
    approved_by: Optional[str]
    approved_at: Optional[datetime]

class BehaviorDrift(BaseModel):
    drift_id: UUID
    baseline_id: UUID
    agent_id: str
    agent_version: str
    drift_type: Literal["decision", "signal", "latency"]
    metric: str
    baseline_value: float
    observed_value: float
    delta: float
    significance: float
    detected_at: datetime
```

### 3. Integration Points

- **Data Source:** Decision and quality aggregated queries
- **APIs:**
  - /v1/baselines/create
  - /v1/drift/run
  - /v1/drift/list
- **UI:** Dashboards consume read-only drift endpoints
- **Alerting:** Optional webhook integration (Slack, PagerDuty)

### 4. File Changes

**Backend**

- server/behavior_profiles.py
- server/baselines.py
- server/drift_engine.py
- server/alerts.py
- server/query_drift.py

**Database**

- server/db/migrations/003_drift_detection.sql

**UI**

- ui/components/BehaviorDashboard.tsx
- ui/components/DriftTimeline.tsx
- ui/components/BaselineManager.tsx

## Implementation Plan

### Step 1: Core Computation

- Behavior profile builder
- Baseline persistence
- Unit tests for distribution math

### Step 2: Drift Detection

- Drift detection engine
- Configurable thresholds
- Drift persistence

### Step 3: Production Readiness

- Alerting integration
- UI dashboards
- Performance tuning
- Feature flags

## Testing Strategy

### Unit Tests

- Distribution calculation correctness
- Drift threshold logic
- Significance calculation
- Baseline immutability

### Integration Tests

- End-to-end baseline → drift detection
- Version comparison scenarios
- Feature flag off → no drift

## Observability

### Logging

- Drift detection start/end
- Baseline creation events
- Alert emission events

### Metrics

- drift_profiles_created_total
- drift_drifts_detected_total
- drift_detection_latency_ms
- drift_alerts_emitted_total

## Future Considerations

### Potential Enhancements

- Multi-baseline comparison
- Seasonal behavior modeling
- User-defined drift metrics

### Known Limitations

- Requires sufficient sample size
- Drift ≠ correctness
- Manual interpretation required

## Dependencies

### Development Dependencies

- Python 3.10+
- NumPy / SciPy (statistical functions)
- SQLAlchemy
- FastAPI
- React + Recharts

## Security Considerations

- No new data ingestion
- No free-text fields
- Read-only access for UI
- Baseline approval audit trail

## Rollout Strategy

1. Development - feature flags off
2. Testing - synthetic drift scenarios
3. Staging - shadow drift detection
4. Production - alerts disabled
5. Gradual alert enablement

## References

- Drift Detection Principles (drift_detection_principles.md)
- AI Assistant Guidelines (ai_guidelines.md)
- Statistical Drift Detection Literature
