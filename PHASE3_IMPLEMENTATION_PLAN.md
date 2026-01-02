# Phase 3 Implementation Plan
## Behavioral Drift Detection & Operational Guardrails

**Created:** 2026-01-02
**Status:** Planning - Ready for Review
**Dependencies:** Phase 1 ✅ Complete, Phase 2 ✅ Complete

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Phase 3 Goals & Scope](#phase-3-goals--scope)
3. [Architecture Overview](#architecture-overview)
4. [Data Models](#data-models)
5. [Backend Components](#backend-components)
6. [API Endpoints](#api-endpoints)
7. [Statistical Methods](#statistical-methods)
8. [UI Components](#ui-components)
9. [Database Migration](#database-migration)
10. [Testing Strategy](#testing-strategy)
11. [Rollout Plan](#rollout-plan)
12. [Observability](#observability)
13. [Constraints & Guardrails](#constraints--guardrails)
14. [Implementation Phases](#implementation-phases)
15. [Success Criteria](#success-criteria)

---

## Executive Summary

### Core Question
> "Has the agent's behavior changed in a way that humans should pay attention to?"

### What Phase 3 Provides
- **Behavioral baseline creation** from Phase 2 data
- **Statistical drift detection** via distribution comparison
- **Informational alerts** when behavior changes significantly
- **Visualization** of behavior stability over time

### What Phase 3 Does NOT Do
- ❌ Judge correctness or quality
- ❌ Modify agent behavior
- ❌ Prescribe fixes or actions
- ❌ Create health scores or rankings
- ❌ Collect new telemetry data

### Key Design Principles
1. **Stability over optimization**
2. **Visibility over control**
3. **Change detection over judgment**
4. **Observational only** - Phase 3 is a "dead-end observer"

---

## Phase 3 Goals & Scope

### Functional Requirements

1. **Behavioral Baseline Creation**
   - Generate stable statistical profiles from Phase 2 data
   - Support version-based baselines (e.g., "v1.0.0 baseline")
   - Support time-window baselines (e.g., "last 7 days")
   - Support manual baselines (human-approved snapshots)
   - Baselines are immutable once created
   - Baselines contain no free text

2. **Drift Detection**
   - Detect statistically significant changes in:
     - Decision distributions (tool selection patterns, retry strategies)
     - Quality signal rates (empty retrievals, schema failures)
     - Behavioral latency patterns
   - Compare live behavior against approved baselines
   - Use statistical tests (KS, Chi-square, Jensen-Shannon divergence)
   - Support configurable significance thresholds

3. **Drift Recording**
   - Persist drift events with full explainability
   - Record baseline used, observed values, statistical significance
   - Never overwrite historical drift records
   - Track drift resolution (when behavior returns to baseline)

4. **Alert Emission**
   - Emit non-blocking alerts for detected drift
   - Alerts describe what changed, not what to do
   - Reference the baseline used
   - Support optional webhook integration (Slack, PagerDuty)

5. **UI Visualization**
   - Show baseline vs observed behavior
   - Visualize drift over time
   - Support drill-down to underlying Phase 2 data
   - No single "health score" or agent rankings

### Non-Functional Requirements

**Performance:**
- Drift detection runs asynchronously (background jobs)
- Aggregation queries do not block ingest
- P95 drift computation < 5 seconds per agent
- Support incremental computation

**Scalability:**
- Support millions of runs (Phase 1 & 2 data)
- Support thousands of agents
- Baselines are cacheable and reusable
- Efficient time-series queries

**Observability:**
- Phase 3 emits its own metrics
- Drift detection is auditable and explainable
- Logging at all computation stages

**Security:**
- No new sensitive data introduced
- Baselines contain no prompts/responses/reasoning
- All derived data is privacy-safe

---

## Architecture Overview

### System Layers

```
┌─────────────────────────────────────────────────────────────┐
│                         Phase 3 UI                          │
│   BehaviorDashboard | DriftTimeline | BaselineManager       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Phase 3 Query API                        │
│   GET /v1/baselines | GET /v1/drift | GET /v1/profiles     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Phase 3 Backend Services                  │
│  BehaviorProfileBuilder | DriftDetectionEngine | AlertEmitter│
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Phase 3 Database Tables                  │
│  behavior_profiles | behavior_baselines | behavior_drift    │
└─────────────────────────────────────────────────────────────┘
                              ↑
                    Reads from Phase 2 ↓
┌─────────────────────────────────────────────────────────────┐
│                 Phase 2 Tables (Read-Only)                  │
│         agent_decisions | agent_quality_signals             │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Phase 2 Data (decisions, signals)
         ↓
Aggregation Query (time window)
         ↓
BehaviorProfileBuilder
         ↓
BehaviorProfile (statistical snapshot)
         ↓
Manual Approval (optional)
         ↓
BehaviorBaseline (immutable)
         ↓
Live Behavior Observation
         ↓
DriftDetectionEngine (statistical comparison)
         ↓
BehaviorDrift (if significant)
         ↓
AlertEmitter (webhooks, notifications)
```

### Component Interaction

```
┌───────────────┐       ┌──────────────────┐       ┌────────────┐
│ Scheduler     │──────▶│ ProfileBuilder   │──────▶│ Database   │
│ (cron/celery) │       │ (aggregation)    │       │ (profiles) │
└───────────────┘       └──────────────────┘       └────────────┘
                                                           │
                                                           ▼
┌───────────────┐       ┌──────────────────┐       ┌────────────┐
│ Scheduler     │──────▶│ DriftEngine      │──────▶│ Database   │
│ (periodic)    │       │ (comparison)     │       │ (drift)    │
└───────────────┘       └──────────────────┘       └────────────┘
                                │                          │
                                ▼                          ▼
                        ┌──────────────────┐       ┌────────────┐
                        │ AlertEmitter     │       │ Query API  │
                        │ (webhooks)       │       │ (read-only)│
                        └──────────────────┘       └────────────┘
```

---

## Data Models

### 1. BehaviorProfile

**Purpose:** Statistical snapshot of agent behavior over a time window

**Schema:**
```python
class BehaviorProfile(BaseModel):
    """
    Represents aggregated behavioral statistics from Phase 2 data.
    Used to create baselines and detect drift.
    """
    profile_id: UUID
    agent_id: str
    agent_version: str
    environment: str  # production, staging, development

    # Time window for aggregation
    window_start: datetime
    window_end: datetime
    sample_size: int  # Number of runs aggregated

    # Decision distributions (from agent_decisions)
    decision_distributions: dict
    # Example:
    # {
    #   "tool_selection": {
    #     "api": 0.65,
    #     "cache": 0.30,
    #     "database": 0.05
    #   },
    #   "retry_strategy": {
    #     "retry": 0.15,
    #     "no_retry": 0.85
    #   }
    # }

    # Quality signal rates (from agent_quality_signals)
    signal_distributions: dict
    # Example:
    # {
    #   "schema_valid": {
    #     "full_match": 0.92,
    #     "partial_match": 0.06,
    #     "no_match": 0.02
    #   },
    #   "tool_success": {
    #     "first_attempt": 0.88,
    #     "after_retry": 0.10,
    #     "failed": 0.02
    #   }
    # }

    # Latency statistics
    latency_stats: dict
    # Example:
    # {
    #   "mean_run_duration_ms": 1234.5,
    #   "p50_run_duration_ms": 1100.0,
    #   "p95_run_duration_ms": 2300.0,
    #   "p99_run_duration_ms": 3100.0
    # }

    created_at: datetime
```

**Constraints:**
- `decision_distributions` and `signal_distributions` contain only normalized probabilities (0.0 - 1.0)
- No free-text fields
- All distributions must sum to 1.0
- Minimum sample_size required for valid profile (e.g., >= 100 runs)

### 2. BehaviorBaseline

**Purpose:** Immutable approved baseline for drift comparison

**Schema:**
```python
class BehaviorBaseline(BaseModel):
    """
    Immutable baseline representing expected agent behavior.
    Created from BehaviorProfile, optionally approved by humans.
    """
    baseline_id: UUID
    profile_id: UUID  # FK to behavior_profiles
    agent_id: str
    agent_version: str
    environment: str

    baseline_type: Literal["version", "time_window", "manual"]
    # - version: "This is the approved behavior for v1.0.0"
    # - time_window: "This is the behavior from last 30 days"
    # - manual: "Human explicitly approved this snapshot"

    # Optional human approval
    approved_by: Optional[str]  # User ID or email
    approved_at: Optional[datetime]

    # Optional description (privacy-safe only)
    description: Optional[str]  # Max 200 chars, no free text from runs

    # Baseline is active (for drift comparison)
    is_active: bool

    created_at: datetime
```

**Constraints:**
- Once created, baselines are never modified (immutable)
- Only one active baseline per (agent_id, agent_version, environment) at a time
- Baselines reference profiles (data is in profiles, not duplicated)
- `description` must not contain prompts, responses, or reasoning

### 3. BehaviorDrift

**Purpose:** Record of detected behavioral change

**Schema:**
```python
class BehaviorDrift(BaseModel):
    """
    Represents detected drift from baseline behavior.
    Purely observational - does not imply good/bad.
    """
    drift_id: UUID
    baseline_id: UUID  # FK to behavior_baselines
    agent_id: str
    agent_version: str
    environment: str

    drift_type: Literal["decision", "signal", "latency"]

    # Specific metric that drifted
    metric: str  # e.g., "tool_selection.api", "schema_valid.full_match"

    # Baseline value vs observed value
    baseline_value: float
    observed_value: float
    delta: float  # observed - baseline
    delta_percent: float  # (delta / baseline) * 100

    # Statistical significance
    significance: float  # p-value from statistical test
    test_method: str  # "ks_test", "chi_square", "percent_threshold"

    # Severity (informational only)
    severity: Literal["low", "medium", "high"]
    # Based purely on magnitude of change, not quality judgment

    # When drift was detected
    detected_at: datetime

    # Window of observed behavior
    observation_window_start: datetime
    observation_window_end: datetime
    observation_sample_size: int

    # Optional: When drift was resolved (behavior returned to baseline)
    resolved_at: Optional[datetime]

    created_at: datetime
```

**Constraints:**
- Drift is descriptive, not evaluative
- No "quality" or "correctness" fields
- `severity` based purely on magnitude, not judgment
- All values are numeric (no free text)

---

## Backend Components

### 1. BehaviorProfileBuilder

**File:** `backend/behavior_profiles.py`

**Responsibilities:**
- Query Phase 2 data (agent_decisions, agent_quality_signals)
- Aggregate over time windows
- Compute decision distributions
- Compute signal distributions
- Compute latency statistics
- Persist BehaviorProfile records

**Key Methods:**

```python
class BehaviorProfileBuilder:
    """
    Builds statistical behavior profiles from Phase 2 data.
    Read-only with respect to Phase 1 & 2 tables.
    """

    def __init__(self, db: Session):
        self.db = db

    def build_profile(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime,
        min_sample_size: int = 100
    ) -> BehaviorProfile:
        """
        Build a behavior profile from Phase 2 data.

        Returns:
            BehaviorProfile if sufficient data exists

        Raises:
            InsufficientDataError if sample_size < min_sample_size
        """
        pass

    def _compute_decision_distributions(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime
    ) -> dict:
        """
        Aggregate decision distributions from agent_decisions table.

        Example query:
        SELECT decision_type, selected, COUNT(*)
        FROM agent_decisions
        WHERE agent_id = ? AND ...
        GROUP BY decision_type, selected

        Returns normalized distributions.
        """
        pass

    def _compute_signal_distributions(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime
    ) -> dict:
        """
        Aggregate quality signal distributions from agent_quality_signals table.

        Returns normalized distributions.
        """
        pass

    def _compute_latency_stats(
        self,
        agent_id: str,
        agent_version: str,
        environment: str,
        window_start: datetime,
        window_end: datetime
    ) -> dict:
        """
        Compute latency statistics from agent_runs table.

        Returns mean, p50, p95, p99 duration.
        """
        pass

    def _validate_sample_size(self, count: int, min_size: int) -> None:
        """
        Validate that sufficient data exists.

        Raises InsufficientDataError if count < min_size.
        """
        pass
```

**Error Handling:**
- Insufficient data (< min_sample_size): Raise InsufficientDataError
- Missing Phase 2 data: Return empty distributions (handle gracefully)
- Database errors: Log and raise

**Performance Considerations:**
- Use indexed queries on (agent_id, agent_version, environment, created_at)
- Consider materialized views for common aggregations
- Cache profiles for reuse

### 2. BaselineManager

**File:** `backend/baselines.py`

**Responsibilities:**
- Create baselines from profiles
- Approve baselines (human-in-the-loop)
- Activate/deactivate baselines
- List available baselines
- Enforce immutability

**Key Methods:**

```python
class BaselineManager:
    """
    Manages behavioral baselines.
    Enforces immutability and approval workflows.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_baseline(
        self,
        profile_id: UUID,
        baseline_type: str,
        approved_by: Optional[str] = None,
        description: Optional[str] = None
    ) -> BehaviorBaseline:
        """
        Create an immutable baseline from a profile.

        Validates:
        - Profile exists
        - Description is privacy-safe
        - Only one active baseline per (agent, version, env)
        """
        pass

    def approve_baseline(
        self,
        baseline_id: UUID,
        approved_by: str
    ) -> BehaviorBaseline:
        """
        Mark baseline as approved by human.

        Once approved, baseline becomes active.
        """
        pass

    def activate_baseline(self, baseline_id: UUID) -> None:
        """
        Set baseline as active for drift comparison.

        Deactivates any existing active baseline for same (agent, version, env).
        """
        pass

    def deactivate_baseline(self, baseline_id: UUID) -> None:
        """
        Deactivate baseline (stop using for drift detection).

        Does not delete - baselines are immutable.
        """
        pass

    def get_active_baseline(
        self,
        agent_id: str,
        agent_version: str,
        environment: str
    ) -> Optional[BehaviorBaseline]:
        """
        Get currently active baseline for drift comparison.

        Returns None if no active baseline.
        """
        pass

    def list_baselines(
        self,
        agent_id: Optional[str] = None,
        agent_version: Optional[str] = None,
        environment: Optional[str] = None,
        baseline_type: Optional[str] = None
    ) -> List[BehaviorBaseline]:
        """
        List baselines with optional filtering.
        """
        pass
```

**Validation:**
- Ensure description contains no sensitive data (privacy validator)
- Enforce one active baseline per (agent_id, agent_version, environment)
- Prevent modification of existing baselines (immutability)

### 3. DriftDetectionEngine

**File:** `backend/drift_engine.py`

**Responsibilities:**
- Compare observed behavior against baselines
- Run statistical tests (KS, Chi-square, JS divergence)
- Detect significant drift
- Persist drift records
- Calculate severity (based on magnitude only)

**Key Methods:**

```python
class DriftDetectionEngine:
    """
    Detects behavioral drift via statistical comparison.
    Purely observational - does not judge quality.
    """

    def __init__(self, db: Session):
        self.db = db
        self.threshold_config = self._load_thresholds()

    def detect_drift(
        self,
        baseline: BehaviorBaseline,
        observed_window_start: datetime,
        observed_window_end: datetime,
        min_sample_size: int = 100
    ) -> List[BehaviorDrift]:
        """
        Detect drift by comparing baseline to observed behavior.

        Steps:
        1. Build profile for observed window
        2. Compare decision distributions
        3. Compare signal distributions
        4. Compare latency stats
        5. Create drift records for significant changes

        Returns:
            List of BehaviorDrift objects (empty if no drift)
        """
        pass

    def _compare_decision_distributions(
        self,
        baseline_profile: BehaviorProfile,
        observed_profile: BehaviorProfile
    ) -> List[BehaviorDrift]:
        """
        Compare decision distributions using Chi-square test.

        Returns drift records for significant changes.
        """
        pass

    def _compare_signal_distributions(
        self,
        baseline_profile: BehaviorProfile,
        observed_profile: BehaviorProfile
    ) -> List[BehaviorDrift]:
        """
        Compare signal distributions using Chi-square test.

        Returns drift records for significant changes.
        """
        pass

    def _compare_latency_stats(
        self,
        baseline_profile: BehaviorProfile,
        observed_profile: BehaviorProfile
    ) -> List[BehaviorDrift]:
        """
        Compare latency statistics using percent threshold.

        Returns drift records for significant changes.
        """
        pass

    def _run_statistical_test(
        self,
        baseline_dist: dict,
        observed_dist: dict,
        test_method: str
    ) -> Tuple[float, float]:
        """
        Run statistical test to detect significant change.

        Args:
            baseline_dist: Baseline distribution {option: probability}
            observed_dist: Observed distribution {option: probability}
            test_method: "chi_square", "ks_test", "js_divergence"

        Returns:
            (test_statistic, p_value)
        """
        pass

    def _calculate_severity(
        self,
        delta_percent: float,
        drift_type: str
    ) -> str:
        """
        Calculate severity based purely on magnitude of change.

        Not a quality judgment - just change magnitude.

        Returns: "low", "medium", or "high"
        """
        pass

    def _is_significant(
        self,
        p_value: float,
        delta_percent: float,
        drift_type: str
    ) -> bool:
        """
        Determine if drift is statistically significant.

        Uses configurable thresholds from threshold_config.
        """
        pass

    def _load_thresholds(self) -> dict:
        """
        Load drift detection thresholds from config.

        Example:
        {
          "decision_drift": {
            "p_value_threshold": 0.05,
            "min_delta_percent": 10.0
          },
          "signal_drift": {
            "p_value_threshold": 0.05,
            "min_delta_percent": 15.0
          },
          "latency_drift": {
            "min_delta_percent": 20.0
          }
        }
        """
        pass
```

**Statistical Methods:**

1. **Chi-Square Test** (for decision/signal distributions)
   - Tests if two categorical distributions differ significantly
   - Returns p-value (< 0.05 = significant)
   - Requires minimum sample size (>=30)

2. **Kolmogorov-Smirnov Test** (alternative for distributions)
   - Tests if two distributions come from same underlying distribution
   - Non-parametric, works with continuous data

3. **Jensen-Shannon Divergence** (for distribution similarity)
   - Symmetric measure of distribution similarity
   - Returns 0-1 (0 = identical, 1 = completely different)

4. **Percent Threshold** (for latency)
   - Simple percent change threshold
   - E.g., "latency increased >20% = drift"

**Threshold Configuration:**
- Configurable per drift type
- Stored in config file or database
- Defaults provided, overridable by users
- No "magic numbers" - all thresholds explicit

### 4. AlertEmitter

**File:** `backend/alerts.py`

**Responsibilities:**
- Emit alerts when drift is detected
- Format alerts with observational language
- Support multiple channels (webhooks, logs, database)
- Never prescribe actions

**Key Methods:**

```python
class AlertEmitter:
    """
    Emits human-readable alerts for detected drift.
    Alerts are informational, non-blocking, non-judgmental.
    """

    def __init__(self):
        self.webhook_config = self._load_webhook_config()

    def emit(self, drift: BehaviorDrift) -> None:
        """
        Emit alert for detected drift.

        Sends to all configured channels:
        - Database (alert_log table)
        - Webhooks (Slack, PagerDuty)
        - Application logs
        """
        pass

    def _format_alert_message(self, drift: BehaviorDrift) -> str:
        """
        Format drift as human-readable alert message.

        Example:
        "Observed increase in tool_selection.api from 65% to 82% (+17%)
         in production environment for agent support-agent v1.2.0.
         Baseline: baseline_abc123 (created 2026-01-01).
         Statistical significance: p=0.003.
         Detected at: 2026-01-02 14:30:00 UTC."

        Language constraints:
        - Use "observed increase/decrease", "distribution shifted"
        - Avoid "better/worse", "correct/incorrect"
        - Reference baseline used
        - Include statistical significance
        """
        pass

    def _send_webhook(self, message: str, drift: BehaviorDrift) -> None:
        """
        Send alert to configured webhooks (Slack, PagerDuty).

        Webhook payload includes:
        - Alert message (formatted)
        - Drift metadata (agent_id, version, metric)
        - Link to UI (for investigation)
        """
        pass

    def _log_alert(self, message: str, drift: BehaviorDrift) -> None:
        """
        Log alert to application logs.
        """
        pass

    def _persist_alert(self, message: str, drift: BehaviorDrift) -> None:
        """
        Persist alert to database (alert_log table).
        """
        pass

    def _load_webhook_config(self) -> dict:
        """
        Load webhook configuration from environment/config.

        Example:
        {
          "slack": {
            "enabled": true,
            "webhook_url": "https://hooks.slack.com/...",
            "channel": "#agent-alerts"
          },
          "pagerduty": {
            "enabled": false,
            "api_key": "...",
            "service_id": "..."
          }
        }
        """
        pass
```

**Language Constraints:**

Approved phrases:
- "Observed increase from X to Y"
- "Distribution shifted by Z%"
- "Correlates with baseline B"
- "Detected deviation in metric M"
- "Baseline comparison shows change"

Forbidden phrases:
- "Better / Worse"
- "Correct / Incorrect"
- "Optimal / Suboptimal"
- "Fix this"
- "Agent should..."
- "Improve performance"

### 5. QueryPhase3

**File:** `backend/query_phase3.py`

**Responsibilities:**
- Read-only API for Phase 3 data
- Query profiles, baselines, drift records
- Aggregation and filtering
- No write operations

**Key Endpoints:**

```python
# GET /v1/profiles
async def list_profiles(
    agent_id: Optional[str] = None,
    agent_version: Optional[str] = None,
    environment: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[BehaviorProfile]:
    """List behavior profiles with filtering."""
    pass

# GET /v1/profiles/{profile_id}
async def get_profile(profile_id: UUID) -> BehaviorProfile:
    """Get specific behavior profile."""
    pass

# GET /v1/baselines
async def list_baselines(
    agent_id: Optional[str] = None,
    agent_version: Optional[str] = None,
    environment: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
) -> List[BehaviorBaseline]:
    """List baselines with filtering."""
    pass

# GET /v1/baselines/{baseline_id}
async def get_baseline(baseline_id: UUID) -> BehaviorBaseline:
    """Get specific baseline."""
    pass

# GET /v1/drift
async def list_drift(
    agent_id: Optional[str] = None,
    agent_version: Optional[str] = None,
    environment: Optional[str] = None,
    drift_type: Optional[str] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
) -> List[BehaviorDrift]:
    """List drift records with filtering."""
    pass

# GET /v1/drift/{drift_id}
async def get_drift(drift_id: UUID) -> BehaviorDrift:
    """Get specific drift record."""
    pass

# GET /v1/drift/timeline
async def drift_timeline(
    agent_id: str,
    agent_version: Optional[str] = None,
    environment: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> dict:
    """
    Get drift timeline for visualization.

    Returns time-series data suitable for charting.
    """
    pass
```

---

## API Endpoints

### Write Endpoints (Phase 3 Admin)

**POST /v1/baselines/create**
```json
{
  "profile_id": "uuid",
  "baseline_type": "version",
  "description": "Baseline for v1.0.0 production",
  "approved_by": "user@example.com"
}
```
Response: `BehaviorBaseline`

**POST /v1/baselines/{baseline_id}/activate**
```json
{}
```
Response: `{"status": "activated"}`

**POST /v1/baselines/{baseline_id}/deactivate**
```json
{}
```
Response: `{"status": "deactivated"}`

**POST /v1/drift/run**
```json
{
  "agent_id": "support-agent",
  "agent_version": "v1.2.0",
  "environment": "production",
  "window_hours": 24
}
```
Response: `{"drift_detected": true, "drift_count": 3, "drift_ids": [...]}`

### Read Endpoints (Phase 3 Query)

Already covered in QueryPhase3 section above.

---

## Statistical Methods

### 1. Chi-Square Test (Decision & Signal Distributions)

**When to use:**
- Comparing categorical distributions (decision types, signal codes)
- Determining if observed frequencies differ from expected

**Implementation:**
```python
from scipy.stats import chi2_contingency

def chi_square_test(baseline_dist: dict, observed_dist: dict) -> Tuple[float, float]:
    """
    Run Chi-square test on two distributions.

    Args:
        baseline_dist: {"option_a": 0.60, "option_b": 0.40}
        observed_dist: {"option_a": 0.75, "option_b": 0.25}

    Returns:
        (chi2_statistic, p_value)
    """
    # Convert to frequency tables
    # Run chi2_contingency
    # Return statistic and p-value
    pass
```

**Interpretation:**
- p-value < 0.05: Distributions differ significantly
- p-value >= 0.05: No significant difference

**Assumptions:**
- Sample size >= 30 (minimum)
- Expected frequency >= 5 for each category

### 2. Jensen-Shannon Divergence (Alternative)

**When to use:**
- Measuring similarity between probability distributions
- Symmetric alternative to KL divergence

**Implementation:**
```python
from scipy.spatial.distance import jensenshannon

def js_divergence(baseline_dist: dict, observed_dist: dict) -> float:
    """
    Calculate Jensen-Shannon divergence.

    Returns:
        Divergence value (0 = identical, 1 = completely different)
    """
    pass
```

**Threshold:**
- JS divergence > 0.1: Consider significant drift

### 3. Percent Threshold (Latency)

**When to use:**
- Comparing numeric metrics (latency, duration)
- Simple percent change detection

**Implementation:**
```python
def percent_change(baseline: float, observed: float) -> float:
    """
    Calculate percent change from baseline.

    Returns:
        Percent change (e.g., 25.0 for 25% increase)
    """
    if baseline == 0:
        return 0.0
    return ((observed - baseline) / baseline) * 100
```

**Thresholds:**
- Latency: > 20% change = drift
- Decision rate: > 10% change = drift
- Signal rate: > 15% change = drift

### 4. Kolmogorov-Smirnov Test (Optional)

**When to use:**
- Continuous distributions
- Non-parametric alternative to Chi-square

**Implementation:**
```python
from scipy.stats import ks_2samp

def ks_test(baseline_samples: list, observed_samples: list) -> Tuple[float, float]:
    """
    Run KS test on two samples.

    Returns:
        (ks_statistic, p_value)
    """
    pass
```

---

## UI Components

### 1. BehaviorDashboard

**File:** `ui/src/pages/BehaviorDashboard.tsx`

**Purpose:**
- Overview of all agents and their behavioral stability
- High-level drift summary
- Entry point to detailed views

**Features:**
- List agents with active baselines
- Show recent drift events per agent
- Filter by environment, version, drift severity
- Color coding for drift status (no judgmental colors)

**Layout:**
```
┌────────────────────────────────────────────────────────┐
│  Behavior Dashboard                                    │
├────────────────────────────────────────────────────────┤
│  [Filter: All Envs ▼] [Filter: All Agents ▼]         │
├────────────────────────────────────────────────────────┤
│  Agent              | Environment | Baseline  | Drift  │
│  ─────────────────────────────────────────────────────│
│  support-agent      | production  | v1.0.0   | 3 ↗    │
│  billing-agent      | production  | v2.1.0   | 0      │
│  search-agent       | staging     | -        | -      │
└────────────────────────────────────────────────────────┘
```

**Data fetched:**
- GET /v1/baselines (active only)
- GET /v1/drift (recent, unresolved)

### 2. DriftTimeline

**File:** `ui/src/components/DriftTimeline.tsx`

**Purpose:**
- Visualize drift over time for a specific agent
- Time-series chart showing drift events
- Drill-down to drift details

**Features:**
- Line chart with time on x-axis
- Multiple metrics on same chart (with toggle)
- Drift events marked with annotations
- Hover to see drift details
- Click to navigate to drift detail page

**Chart Library:** Recharts (React charting library)

**Layout:**
```
┌────────────────────────────────────────────────────────┐
│  Drift Timeline - support-agent v1.2.0 (production)   │
├────────────────────────────────────────────────────────┤
│  [Metric: All ▼] [Time: Last 30 Days ▼]              │
├────────────────────────────────────────────────────────┤
│                                                        │
│   %                                                    │
│   80│              ●                                   │
│   70│         ●         ●                              │
│   60│    ●                   ●                         │
│   50│                            ●                     │
│      └──────────────────────────────────────────────  │
│       Jan 1    Jan 10   Jan 20   Jan 30              │
│                                                        │
│   ● = Drift event (click for details)                 │
└────────────────────────────────────────────────────────┘
```

**Data fetched:**
- GET /v1/drift/timeline

### 3. BaselineManager

**File:** `ui/src/pages/BaselineManager.tsx`

**Purpose:**
- Manage baselines (create, activate, deactivate)
- View baseline details
- Approve baselines (human-in-the-loop)

**Features:**
- List all baselines for an agent
- Show active vs inactive baselines
- Create new baseline from profile
- Activate/deactivate baselines
- View baseline data (distributions, stats)

**Layout:**
```
┌────────────────────────────────────────────────────────┐
│  Baseline Manager - support-agent v1.2.0              │
├────────────────────────────────────────────────────────┤
│  [+ Create New Baseline]                              │
├────────────────────────────────────────────────────────┤
│  Baseline ID     | Type        | Status   | Actions   │
│  ──────────────────────────────────────────────────── │
│  baseline-abc123 | version     | Active   | [View]    │
│  baseline-def456 | time_window | Inactive | [Activate]│
│  baseline-ghi789 | manual      | Inactive | [View]    │
└────────────────────────────────────────────────────────┘
```

**Actions:**
- Create: Opens modal with profile selection
- Activate: POST /v1/baselines/{id}/activate
- View: Shows baseline details (distributions)

### 4. DriftDetail

**File:** `ui/src/pages/DriftDetail.tsx`

**Purpose:**
- Detailed view of a single drift event
- Compare baseline vs observed distributions
- Drill-down to underlying Phase 2 data

**Features:**
- Show drift metadata (agent, version, metric, detected_at)
- Side-by-side comparison (baseline vs observed)
- Statistical significance display
- Link to baseline used
- Link to underlying runs (Phase 2 data)

**Layout:**
```
┌────────────────────────────────────────────────────────┐
│  Drift Event Details                                   │
├────────────────────────────────────────────────────────┤
│  Agent: support-agent v1.2.0 (production)             │
│  Metric: tool_selection.api                           │
│  Detected: 2026-01-02 14:30:00 UTC                    │
│  Severity: medium                                      │
├────────────────────────────────────────────────────────┤
│  Baseline vs Observed                                  │
│  ────────────────────────────────────────────────────  │
│  Baseline (from baseline-abc123):        65%          │
│  Observed (Jan 1-2, 2026):               82%          │
│  Delta:                                  +17%          │
│  Statistical Significance:               p=0.003       │
├────────────────────────────────────────────────────────┤
│  Distribution Comparison                               │
│  ────────────────────────────────────────────────────  │
│  [Bar chart showing baseline vs observed]             │
└────────────────────────────────────────────────────────┘
```

**Data fetched:**
- GET /v1/drift/{drift_id}
- GET /v1/baselines/{baseline_id}

---

## Database Migration

**File:** `db/migrations/003_phase3_behavior.sql`

### Tables to Create

#### 1. behavior_profiles

```sql
CREATE TABLE behavior_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) NOT NULL,
    agent_version VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL,

    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    sample_size INTEGER NOT NULL CHECK (sample_size >= 0),

    decision_distributions JSONB NOT NULL DEFAULT '{}',
    signal_distributions JSONB NOT NULL DEFAULT '{}',
    latency_stats JSONB NOT NULL DEFAULT '{}',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_profile UNIQUE (agent_id, agent_version, environment, window_start, window_end)
);

CREATE INDEX idx_behavior_profiles_agent ON behavior_profiles(agent_id, agent_version, environment);
CREATE INDEX idx_behavior_profiles_window ON behavior_profiles(window_start, window_end);
```

#### 2. behavior_baselines

```sql
CREATE TABLE behavior_baselines (
    baseline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES behavior_profiles(profile_id) ON DELETE CASCADE,

    agent_id VARCHAR(255) NOT NULL,
    agent_version VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL,

    baseline_type VARCHAR(50) NOT NULL CHECK (baseline_type IN ('version', 'time_window', 'manual')),

    approved_by VARCHAR(255),
    approved_at TIMESTAMP,
    description VARCHAR(200),

    is_active BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_active_baseline UNIQUE (agent_id, agent_version, environment, is_active)
        WHERE is_active = TRUE
);

CREATE INDEX idx_behavior_baselines_agent ON behavior_baselines(agent_id, agent_version, environment);
CREATE INDEX idx_behavior_baselines_active ON behavior_baselines(is_active) WHERE is_active = TRUE;
```

#### 3. behavior_drift

```sql
CREATE TABLE behavior_drift (
    drift_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    baseline_id UUID NOT NULL REFERENCES behavior_baselines(baseline_id) ON DELETE CASCADE,

    agent_id VARCHAR(255) NOT NULL,
    agent_version VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL,

    drift_type VARCHAR(50) NOT NULL CHECK (drift_type IN ('decision', 'signal', 'latency')),
    metric VARCHAR(255) NOT NULL,

    baseline_value FLOAT NOT NULL,
    observed_value FLOAT NOT NULL,
    delta FLOAT NOT NULL,
    delta_percent FLOAT NOT NULL,

    significance FLOAT NOT NULL,
    test_method VARCHAR(50) NOT NULL,

    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high')),

    detected_at TIMESTAMP NOT NULL,
    observation_window_start TIMESTAMP NOT NULL,
    observation_window_end TIMESTAMP NOT NULL,
    observation_sample_size INTEGER NOT NULL,

    resolved_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_behavior_drift_agent ON behavior_drift(agent_id, agent_version, environment);
CREATE INDEX idx_behavior_drift_detected ON behavior_drift(detected_at DESC);
CREATE INDEX idx_behavior_drift_resolved ON behavior_drift(resolved_at) WHERE resolved_at IS NULL;
```

#### 4. alert_log (Optional)

```sql
CREATE TABLE alert_log (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drift_id UUID NOT NULL REFERENCES behavior_drift(drift_id) ON DELETE CASCADE,

    alert_message TEXT NOT NULL,
    alert_channel VARCHAR(50) NOT NULL, -- 'slack', 'pagerduty', 'email'

    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivery_status VARCHAR(50) DEFAULT 'sent' -- 'sent', 'failed', 'pending'
);

CREATE INDEX idx_alert_log_drift ON alert_log(drift_id);
CREATE INDEX idx_alert_log_sent ON alert_log(sent_at DESC);
```

### Privacy Enforcement Trigger

```sql
-- Ensure no sensitive data in baseline descriptions
CREATE OR REPLACE FUNCTION validate_baseline_description()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.description IS NOT NULL THEN
        -- Check for blocked keywords
        IF NEW.description ~* '(prompt|response|reasoning|thought|message|content)' THEN
            RAISE EXCEPTION 'Baseline description contains forbidden keywords';
        END IF;

        -- Check length
        IF LENGTH(NEW.description) > 200 THEN
            RAISE EXCEPTION 'Baseline description too long (max 200 chars)';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_baseline_description
BEFORE INSERT OR UPDATE ON behavior_baselines
FOR EACH ROW
EXECUTE FUNCTION validate_baseline_description();
```

### Rollback Plan

```sql
-- Rollback script (separate file: 003_phase3_behavior_rollback.sql)
DROP TABLE IF EXISTS alert_log CASCADE;
DROP TABLE IF EXISTS behavior_drift CASCADE;
DROP TABLE IF EXISTS behavior_baselines CASCADE;
DROP TABLE IF EXISTS behavior_profiles CASCADE;

DROP FUNCTION IF EXISTS validate_baseline_description CASCADE;
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_phase3_behavior_profiles.py`

**Test Coverage:**
1. **BehaviorProfileBuilder**
   - Test decision distribution aggregation
   - Test signal distribution aggregation
   - Test latency statistics computation
   - Test insufficient data handling
   - Test empty Phase 2 data handling
   - Test normalization (distributions sum to 1.0)

**File:** `tests/test_phase3_drift_detection.py`

**Test Coverage:**
2. **DriftDetectionEngine**
   - Test Chi-square drift detection
   - Test JS divergence drift detection
   - Test percent threshold drift detection
   - Test severity calculation
   - Test significance thresholds
   - Test no drift scenario (baseline == observed)
   - Test edge cases (zero baseline, missing keys)

**File:** `tests/test_phase3_baselines.py`

**Test Coverage:**
3. **BaselineManager**
   - Test baseline creation
   - Test baseline activation/deactivation
   - Test immutability enforcement
   - Test unique active baseline constraint
   - Test privacy validation (description)
   - Test approval workflow

**File:** `tests/test_phase3_alerts.py`

**Test Coverage:**
4. **AlertEmitter**
   - Test alert formatting (observational language)
   - Test webhook sending
   - Test alert persistence
   - Test language constraints (no judgmental terms)

### Integration Tests

**File:** `tests/test_phase3_integration.py`

**Test Scenarios:**
1. **End-to-End Baseline Creation**
   - Create Phase 2 data (decisions, signals)
   - Build profile from Phase 2 data
   - Create baseline from profile
   - Activate baseline
   - Verify database state

2. **End-to-End Drift Detection**
   - Create baseline (stable behavior)
   - Create Phase 2 data with drift (changed behavior)
   - Run drift detection
   - Verify drift records created
   - Verify alerts emitted

3. **Version Comparison**
   - Create baseline for v1.0.0
   - Create Phase 2 data for v1.1.0 (different behavior)
   - Run drift detection
   - Verify drift detected between versions

4. **No Drift Scenario**
   - Create baseline
   - Create Phase 2 data matching baseline
   - Run drift detection
   - Verify no drift detected

5. **Feature Flag Disabled**
   - Disable Phase 3 feature flag
   - Verify Phase 1 & 2 unaffected
   - Verify no drift detection runs

### Performance Tests

**File:** `tests/test_phase3_performance.py`

**Test Scenarios:**
1. **Profile Building Performance**
   - Test with 1K runs
   - Test with 10K runs
   - Test with 100K runs
   - Verify P95 < 5 seconds

2. **Drift Detection Performance**
   - Test single agent drift detection
   - Test 100 agents drift detection
   - Verify efficient queries (indexed)

### Statistical Correctness Tests

**File:** `tests/test_phase3_statistics.py`

**Test Scenarios:**
1. **Chi-Square Test Accuracy**
   - Test with known distributions
   - Verify p-value calculation
   - Test edge cases (small samples)

2. **JS Divergence Accuracy**
   - Test with identical distributions (should = 0)
   - Test with completely different distributions (should ≈ 1)

3. **Percent Threshold Accuracy**
   - Test positive change
   - Test negative change
   - Test zero baseline handling

---

## Rollout Plan

### Phase 1: Development (Feature Flags Off)

**Timeline:** Weeks 1-2

**Activities:**
1. Implement backend components
   - BehaviorProfileBuilder
   - BaselineManager
   - DriftDetectionEngine
   - AlertEmitter
   - QueryPhase3

2. Database migration (003_phase3_behavior.sql)

3. Unit tests (44+ tests target)

4. Feature flag: `PHASE3_ENABLED=false`

**Success Criteria:**
- All unit tests passing
- No regressions in Phase 1 & 2
- Code review approved
- Documentation complete

### Phase 2: Synthetic Testing (Feature Flags On, Staging)

**Timeline:** Week 3

**Activities:**
1. Deploy to staging environment
2. Feature flag: `PHASE3_ENABLED=true` (staging only)
3. Create synthetic drift scenarios:
   - Baseline with stable behavior
   - Introduce drift (change decision distributions)
   - Verify drift detected
4. Test UI components
5. Test alert emission

**Success Criteria:**
- Synthetic drift detected correctly
- UI displays drift events
- Alerts formatted correctly
- No false positives
- Performance within SLA (P95 < 5s)

### Phase 3: Shadow Mode (Production, Alerts Disabled)

**Timeline:** Week 4

**Activities:**
1. Deploy to production
2. Feature flag: `PHASE3_ENABLED=true`, `PHASE3_ALERTS_ENABLED=false`
3. Run drift detection on real data
4. Collect metrics (drift detection latency, false positives)
5. Manual review of detected drift
6. Tune thresholds based on findings

**Success Criteria:**
- Drift detection runs without errors
- Performance within SLA
- Manual review confirms drift is meaningful
- No impact on Phase 1 & 2 performance

### Phase 4: Gradual Alert Enablement

**Timeline:** Week 5

**Activities:**
1. Enable alerts for single agent (canary)
2. Monitor alert volume and quality
3. Gradually enable for more agents
4. Collect user feedback

**Success Criteria:**
- Alert volume manageable (<10/day initially)
- Users find alerts actionable
- No alert fatigue
- False positive rate < 5%

### Phase 5: Full Production

**Timeline:** Week 6+

**Activities:**
1. Enable for all agents
2. Feature flag: `PHASE3_ALERTS_ENABLED=true` (all)
3. Monitor and iterate on thresholds
4. Collect user feedback
5. Plan Phase 4 enhancements

**Success Criteria:**
- Drift detection stable and reliable
- Users actively using baselines
- Alerts providing value
- System performance stable

---

## Observability

### Metrics to Emit

**Phase 3 Metrics:**

```python
# Profile building
phase3_profiles_created_total  # Counter
phase3_profile_build_latency_ms  # Histogram
phase3_profile_build_errors_total  # Counter

# Baseline management
phase3_baselines_created_total  # Counter
phase3_baselines_activated_total  # Counter
phase3_baselines_deactivated_total  # Counter

# Drift detection
phase3_drift_detection_runs_total  # Counter
phase3_drifts_detected_total  # Counter (by drift_type, severity)
phase3_drift_detection_latency_ms  # Histogram
phase3_drift_detection_errors_total  # Counter

# Alerts
phase3_alerts_emitted_total  # Counter (by channel)
phase3_alert_delivery_failures_total  # Counter (by channel)

# Query API
phase3_api_requests_total  # Counter (by endpoint)
phase3_api_latency_ms  # Histogram (by endpoint)
phase3_api_errors_total  # Counter (by endpoint, status_code)
```

### Logging

**Log Levels:**

- **INFO:** Drift detection started/completed, baseline created/activated
- **WARNING:** Drift detected (with metadata)
- **ERROR:** Drift detection failed, alert delivery failed
- **DEBUG:** Statistical test details, threshold calculations

**Log Format:**
```json
{
  "timestamp": "2026-01-02T14:30:00Z",
  "level": "WARNING",
  "component": "DriftDetectionEngine",
  "event": "drift_detected",
  "agent_id": "support-agent",
  "agent_version": "v1.2.0",
  "environment": "production",
  "drift_type": "decision",
  "metric": "tool_selection.api",
  "delta_percent": 17.0,
  "significance": 0.003,
  "severity": "medium"
}
```

### Health Checks

**Phase 3 Health Endpoint:**

```python
# GET /v1/phase3/health
async def phase3_health() -> dict:
    """
    Phase 3 health check.

    Returns:
    {
      "status": "healthy",
      "checks": {
        "database": "ok",
        "drift_detection": "ok",
        "alerts": "ok"
      },
      "metrics": {
        "active_baselines": 42,
        "drift_events_last_24h": 5,
        "profile_build_p95_ms": 1234
      }
    }
    """
    pass
```

---

## Constraints & Guardrails

### Enforcement Mechanisms

#### 1. SDK Layer (Not Applicable)
Phase 3 does not introduce SDK changes. All data comes from existing Phase 2.

#### 2. API Layer

**Privacy Validation:**
```python
def validate_baseline_description(description: Optional[str]) -> None:
    """
    Validate baseline description is privacy-safe.

    Raises ValueError if description contains forbidden keywords.
    """
    if description is None:
        return

    forbidden_keywords = [
        'prompt', 'response', 'reasoning', 'thought',
        'message', 'content', 'text', 'output', 'input',
        'chain_of_thought', 'explanation', 'rationale'
    ]

    for keyword in forbidden_keywords:
        if keyword in description.lower():
            raise ValueError(f"Forbidden keyword '{keyword}' in description")

    if len(description) > 200:
        raise ValueError("Description too long (max 200 chars)")
```

**Language Validation:**
```python
def validate_alert_language(message: str) -> None:
    """
    Validate alert message uses observational language only.

    Raises ValueError if judgmental language detected.
    """
    forbidden_phrases = [
        'better', 'worse', 'correct', 'incorrect',
        'optimal', 'suboptimal', 'fix this', 'agent should',
        'improve performance', 'degraded quality'
    ]

    message_lower = message.lower()
    for phrase in forbidden_phrases:
        if phrase in message_lower:
            raise ValueError(f"Forbidden phrase '{phrase}' in alert message")
```

#### 3. Database Layer

**Immutability Enforcement:**
```sql
-- Prevent updates to behavior_baselines (immutable)
CREATE OR REPLACE FUNCTION prevent_baseline_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Allow activation/deactivation only
    IF OLD.is_active != NEW.is_active THEN
        RETURN NEW;
    END IF;

    -- Prevent all other updates
    RAISE EXCEPTION 'Baselines are immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_baseline_update
BEFORE UPDATE ON behavior_baselines
FOR EACH ROW
EXECUTE FUNCTION prevent_baseline_update();
```

**Privacy Trigger:**
(Already covered in Database Migration section)

#### 4. Code Review Checklist

Before merging Phase 3 code, verify:

- [ ] No agent behavior modification
- [ ] No Phase 1 or Phase 2 table modifications
- [ ] No privacy boundary violations (no prompts/responses accessed)
- [ ] No evaluative language in alerts or UI
- [ ] No feedback loops or control logic
- [ ] No optimization or tuning logic
- [ ] Baselines are immutable
- [ ] Drift is descriptive, not judgmental
- [ ] Alerts are informational only
- [ ] Statistical methods are explicit and documented
- [ ] All language is observational (approved phrases only)

---

## Implementation Phases

### Phase 1: Core Computation (Weeks 1-2)

**Deliverables:**
1. `backend/behavior_profiles.py` - BehaviorProfileBuilder
2. `backend/baselines.py` - BaselineManager
3. `db/migrations/003_phase3_behavior.sql` - Database schema
4. `tests/test_phase3_behavior_profiles.py` - Unit tests
5. `tests/test_phase3_baselines.py` - Unit tests

**Success Criteria:**
- Profiles can be built from Phase 2 data
- Baselines can be created and activated
- All unit tests passing
- Feature flag: `PHASE3_ENABLED=false`

### Phase 2: Drift Detection (Week 3)

**Deliverables:**
1. `backend/drift_engine.py` - DriftDetectionEngine
2. `backend/alerts.py` - AlertEmitter
3. `tests/test_phase3_drift_detection.py` - Unit tests
4. `tests/test_phase3_alerts.py` - Unit tests
5. `tests/test_phase3_integration.py` - Integration tests

**Success Criteria:**
- Drift can be detected using statistical tests
- Alerts can be emitted
- Integration tests passing
- Synthetic drift scenarios verified

### Phase 3: Production Readiness (Week 4)

**Deliverables:**
1. `backend/query_phase3.py` - Query API endpoints
2. `ui/src/pages/BehaviorDashboard.tsx` - UI dashboard
3. `ui/src/components/DriftTimeline.tsx` - Drift visualization
4. `ui/src/pages/BaselineManager.tsx` - Baseline management
5. `ui/src/pages/DriftDetail.tsx` - Drift detail view
6. `docs/phase3-drift-detection.md` - Comprehensive guide

**Success Criteria:**
- All API endpoints functional
- UI components complete
- Documentation complete
- Performance testing passed
- Ready for staging deployment

---

## Success Criteria

### Functional Success Criteria

- [ ] Baselines can be created from Phase 2 data
- [ ] Drift detection runs asynchronously without blocking
- [ ] Drift is detected for decision distributions
- [ ] Drift is detected for signal distributions
- [ ] Drift is detected for latency patterns
- [ ] Alerts are emitted when drift is detected
- [ ] Alerts use observational language only
- [ ] UI displays baselines, drift timeline, and drift details
- [ ] Baselines are immutable once created
- [ ] Only one active baseline per (agent, version, env)

### Non-Functional Success Criteria

- [ ] P95 drift detection latency < 5 seconds
- [ ] No impact on Phase 1 & 2 ingest performance
- [ ] Database queries use indexes efficiently
- [ ] Privacy enforcement at all layers (SDK, API, DB)
- [ ] All unit tests passing (44+ tests)
- [ ] Integration tests passing (5+ scenarios)
- [ ] Code coverage > 85%
- [ ] Documentation complete and accurate

### Design Principles Success Criteria

- [ ] Phase 3 is observational only (no agent modification)
- [ ] No new data collection (derives from Phase 2)
- [ ] No quality scores or agent rankings
- [ ] Drift is descriptive, not evaluative
- [ ] Alerts are informational, not prescriptive
- [ ] Human-in-the-loop boundary preserved
- [ ] Backward compatible with Phase 1 & 2
- [ ] No regressions in existing features

### User Experience Success Criteria

- [ ] Users can create baselines with <5 clicks
- [ ] Drift events are understandable without technical knowledge
- [ ] UI is intuitive and requires no training
- [ ] Alerts provide enough context for investigation
- [ ] False positive rate < 5%
- [ ] Alert volume manageable (<10/day per team)

---

## Appendix A: Threshold Configuration

**File:** `config/drift_thresholds.yaml`

```yaml
drift_detection:
  decision_drift:
    # Statistical significance threshold (p-value)
    p_value_threshold: 0.05

    # Minimum percent change to consider
    min_delta_percent: 10.0

    # Test method
    test_method: "chi_square"

  signal_drift:
    p_value_threshold: 0.05
    min_delta_percent: 15.0
    test_method: "chi_square"

  latency_drift:
    # No statistical test, just percent threshold
    min_delta_percent: 20.0
    test_method: "percent_threshold"

severity_thresholds:
  # Based on delta_percent magnitude
  low:
    max_delta_percent: 15.0
  medium:
    max_delta_percent: 30.0
  high:
    # > 30% = high

minimum_sample_sizes:
  profile: 100  # Minimum runs to build valid profile
  drift_detection: 50  # Minimum runs for drift comparison
```

---

## Appendix B: Alert Templates

**Slack Alert Template:**

```
⚠️ Behavioral Drift Detected

**Agent:** {agent_id} v{agent_version} ({environment})
**Metric:** {metric}
**Change:** {baseline_value} → {observed_value} ({delta_percent:+.1f}%)
**Severity:** {severity}

**Baseline:** {baseline_id} (created {baseline_created_at})
**Statistical Significance:** p={significance:.4f}
**Detected:** {detected_at}

**Observation Window:** {observation_window_start} to {observation_window_end} ({observation_sample_size} runs)

[View Details](https://platform.example.com/drift/{drift_id})
```

**PagerDuty Alert Template:**

```json
{
  "routing_key": "{pagerduty_routing_key}",
  "event_action": "trigger",
  "payload": {
    "summary": "Behavioral drift detected: {agent_id} v{agent_version} - {metric}",
    "severity": "{severity}",
    "source": "AgentTracer Phase 3",
    "custom_details": {
      "agent_id": "{agent_id}",
      "agent_version": "{agent_version}",
      "environment": "{environment}",
      "metric": "{metric}",
      "baseline_value": {baseline_value},
      "observed_value": {observed_value},
      "delta_percent": {delta_percent},
      "significance": {significance},
      "baseline_id": "{baseline_id}",
      "drift_id": "{drift_id}"
    }
  }
}
```

---

## Appendix C: Files to Create/Modify

### New Files (13)

**Backend:**
1. `backend/behavior_profiles.py` (BehaviorProfileBuilder)
2. `backend/baselines.py` (BaselineManager)
3. `backend/drift_engine.py` (DriftDetectionEngine)
4. `backend/alerts.py` (AlertEmitter)
5. `backend/query_phase3.py` (Query API endpoints)

**Database:**
6. `db/migrations/003_phase3_behavior.sql` (Schema)
7. `db/migrations/003_phase3_behavior_rollback.sql` (Rollback)

**UI:**
8. `ui/src/pages/BehaviorDashboard.tsx`
9. `ui/src/components/DriftTimeline.tsx`
10. `ui/src/pages/BaselineManager.tsx`
11. `ui/src/pages/DriftDetail.tsx`

**Documentation:**
12. `docs/phase3-drift-detection.md` (Comprehensive guide)

**Configuration:**
13. `config/drift_thresholds.yaml` (Threshold config)

### Modified Files (7)

**Backend:**
1. `backend/main.py` (Add Phase 3 endpoints)

**Tests:**
2. `tests/test_phase3_behavior_profiles.py` (New)
3. `tests/test_phase3_drift_detection.py` (New)
4. `tests/test_phase3_baselines.py` (New)
5. `tests/test_phase3_alerts.py` (New)
6. `tests/test_phase3_integration.py` (New)

**Documentation:**
7. `README.md` (Update with Phase 3 status)

---

## End of Implementation Plan

This plan provides a complete roadmap for Phase 3 implementation without writing any code. All components, data models, APIs, UI, testing, and rollout strategies are defined in detail, ready for implementation.

**Next Steps:**
1. Review this plan with stakeholders
2. Get approval on architecture and approach
3. Begin Phase 1 implementation (Core Computation)
4. Follow rollout plan through to production

**Questions or Clarifications:**
- Threshold values can be tuned based on user feedback
- Webhook integrations are optional (can start with database + logs)
- UI components can be simplified for MVP
- Statistical methods can be extended (KS test, etc.) if needed

**Strict Adherence to Constraints:**
This plan follows all constraints from `claude.md` and `context.md`:
- ✅ Observational only
- ✅ No agent behavior modification
- ✅ No new data collection
- ✅ Privacy-safe throughout
- ✅ Additive to Phase 1 & 2
- ✅ Drift is descriptive, not evaluative
- ✅ Alerts are informational only
- ✅ Human-in-the-loop preserved
