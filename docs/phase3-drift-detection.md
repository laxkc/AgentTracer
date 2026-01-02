# Phase 3 - Behavioral Drift Detection & Guardrails

**Status:** ✅ Complete
**Version:** 1.0.0
**Date:** 2026-01-02

---

## Table of Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Architecture](#architecture)
4. [Data Models](#data-models)
5. [API Reference](#api-reference)
6. [Statistical Methods](#statistical-methods)
7. [Configuration](#configuration)
8. [Usage Guide](#usage-guide)
9. [Constraints & Guardrails](#constraints--guardrails)
10. [Examples](#examples)

---

## Overview

### What is Phase 3?

Phase 3 provides **behavioral drift detection** - the ability to detect when an agent's behavior has changed significantly from an established baseline.

**Core Question:**
> "Has the agent's behavior changed in a way that humans should pay attention to?"

### What Phase 3 Does

- ✅ **Baseline Creation**: Creates statistical snapshots of agent behavior
- ✅ **Drift Detection**: Detects statistically significant behavioral changes
- ✅ **Informational Alerts**: Emits neutral alerts when drift is detected
- ✅ **Visualization**: Provides data for drift timeline visualization

### What Phase 3 Does NOT Do

- ❌ **Judge Correctness**: Drift does not mean "bad" or "broken"
- ❌ **Modify Behavior**: Phase 3 is purely observational
- ❌ **Prescribe Actions**: Alerts describe what changed, not what to do
- ❌ **Create Health Scores**: No single quality or health metrics
- ❌ **Rank Agents**: No comparative quality judgments

### Key Principles

1. **Observational Only** - Phase 3 never influences agent behavior
2. **Neutral Language** - "Observed increase", not "degraded" or "improved"
3. **Statistical Rigor** - Uses Chi-square tests, not heuristics
4. **Human-in-the-Loop** - Humans decide what to do about drift
5. **Privacy-Safe** - Derives from Phase 2, no prompts/responses

---

## Core Concepts

### Behavioral Baseline

An **immutable snapshot** of expected agent behavior, created from historical Phase 2 data.

**Characteristics:**
- Immutable once created (except activation status)
- Contains statistical distributions, not raw data
- References a behavior profile
- Can be version-based, time-window-based, or manually approved

**Example:**
```
Baseline for support-agent v1.0.0 (production)
- Decision distribution: API calls 65%, cache 30%, DB 5%
- Quality signals: Schema valid 92%, tool success 88%
- Latency: Mean 1234ms, P95 2300ms
```

### Behavioral Drift

A **statistically significant change** in agent behavior relative to a baseline.

**Important:** Drift is **descriptive**, not **evaluative**.

- ✅ Drift = "Behavior changed"
- ❌ Drift ≠ "Behavior degraded"
- ❌ Drift ≠ "Agent is broken"
- ❌ Drift ≠ "Quality decreased"

**Drift can be:**
- Intentional (new version, configuration change)
- Environmental (external API changes, load patterns)
- Unintentional (regression, silent bug)

**Human interpretation required** to determine if action is needed.

### Drift Types

1. **Decision Drift**: Changes in decision distributions
   - Example: Tool selection changed from 65% API to 82% API

2. **Signal Drift**: Changes in quality signal rates
   - Example: Schema validation failures increased from 2% to 8%

3. **Latency Drift**: Changes in performance patterns
   - Example: P95 latency increased from 2.3s to 3.1s (35%)

---

## Architecture

### Component Overview

```
Phase 2 Data (decisions, signals)
         ↓
BehaviorProfileBuilder (aggregation)
         ↓
BehaviorProfile (statistical snapshot)
         ↓
BaselineManager (create immutable baseline)
         ↓
BehaviorBaseline (approved baseline)
         ↓
DriftDetectionEngine (statistical comparison)
         ↓
BehaviorDrift (detected changes)
         ↓
AlertEmitter (informational alerts)
```

### Components

#### 1. BehaviorProfileBuilder

**Purpose:** Aggregate Phase 2 data into statistical profiles

**File:** `backend/behavior_profiles.py`

**Key Methods:**
- `build_profile()` - Creates statistical snapshot from time window
- `_compute_decision_distributions()` - Aggregates decision data
- `_compute_signal_distributions()` - Aggregates quality signals
- `_compute_latency_stats()` - Computes latency statistics

**Input:** Phase 2 data (agent_decisions, agent_quality_signals)
**Output:** BehaviorProfile (ready for baseline creation)

#### 2. BaselineManager

**Purpose:** Create and manage immutable baselines

**File:** `backend/baselines.py`

**Key Methods:**
- `create_baseline()` - Creates immutable baseline from profile
- `activate_baseline()` - Sets baseline as active for drift detection
- `deactivate_baseline()` - Deactivates baseline
- `approve_baseline()` - Human approval workflow

**Constraints:**
- Baselines are immutable (cannot be modified)
- Only one active baseline per (agent, version, environment)
- Descriptions must be privacy-safe

#### 3. DriftDetectionEngine

**Purpose:** Detect behavioral drift via statistical comparison

**File:** `backend/drift_engine.py`

**Key Methods:**
- `detect_drift()` - Compares observed behavior to baseline
- `_compare_decision_distributions()` - Chi-square test on decisions
- `_compare_signal_distributions()` - Chi-square test on signals
- `_compare_latency_stats()` - Percent threshold on latency

**Statistical Methods:**
- Chi-square test (decision/signal distributions)
- Percent threshold (latency changes)
- Configurable significance thresholds

#### 4. AlertEmitter

**Purpose:** Emit informational alerts for drift

**File:** `backend/alerts.py`

**Key Methods:**
- `emit()` - Sends alert to all configured channels
- `_format_alert_message()` - Formats neutral alert message
- `_send_slack_webhook()` - Slack integration
- `_send_pagerduty_alert()` - PagerDuty integration

**Language Constraints:**
- ✅ "Observed increase/decrease"
- ✅ "Distribution shifted"
- ❌ "Better/worse"
- ❌ "Degraded/improved"

---

## Data Models

### BehaviorProfile

Statistical snapshot of agent behavior over a time window.

```python
{
  "profile_id": "uuid",
  "agent_id": "support-agent",
  "agent_version": "v1.0.0",
  "environment": "production",

  "window_start": "2026-01-01T00:00:00Z",
  "window_end": "2026-01-07T23:59:59Z",
  "sample_size": 1234,

  "decision_distributions": {
    "tool_selection": {
      "api": 0.65,
      "cache": 0.30,
      "database": 0.05
    }
  },

  "signal_distributions": {
    "schema_valid": {
      "full_match": 0.92,
      "partial_match": 0.06,
      "no_match": 0.02
    }
  },

  "latency_stats": {
    "mean_run_duration_ms": 1234.5,
    "p50_run_duration_ms": 1100.0,
    "p95_run_duration_ms": 2300.0,
    "p99_run_duration_ms": 3100.0
  }
}
```

### BehaviorBaseline

Immutable approved baseline for drift comparison.

```python
{
  "baseline_id": "uuid",
  "profile_id": "uuid",

  "agent_id": "support-agent",
  "agent_version": "v1.0.0",
  "environment": "production",

  "baseline_type": "version",  # or "time_window", "manual"

  "approved_by": "user@example.com",
  "approved_at": "2026-01-01T12:00:00Z",
  "description": "Baseline for v1.0.0 production release",

  "is_active": true,
  "created_at": "2026-01-01T12:00:00Z"
}
```

### BehaviorDrift

Record of detected behavioral change.

```python
{
  "drift_id": "uuid",
  "baseline_id": "uuid",

  "agent_id": "support-agent",
  "agent_version": "v1.0.0",
  "environment": "production",

  "drift_type": "decision",  # or "signal", "latency"
  "metric": "tool_selection.api",

  "baseline_value": 0.65,
  "observed_value": 0.82,
  "delta": 0.17,
  "delta_percent": 26.15,

  "significance": 0.003,  # p-value
  "test_method": "chi_square",

  "severity": "medium",  # based on magnitude, not quality

  "detected_at": "2026-01-02T14:30:00Z",
  "observation_window_start": "2026-01-01T00:00:00Z",
  "observation_window_end": "2026-01-02T23:59:59Z",
  "observation_sample_size": 456,

  "resolved_at": null  # when drift resolved (behavior returns to baseline)
}
```

---

## API Reference

All Phase 3 endpoints are under `/v1/phase3` and are read-only.

### Profiles

**List Profiles**
```
GET /v1/phase3/profiles?agent_id=support-agent&limit=100
```

**Get Profile**
```
GET /v1/phase3/profiles/{profile_id}
```

### Baselines

**List Baselines**
```
GET /v1/phase3/baselines?agent_id=support-agent&is_active=true
```

**Get Baseline**
```
GET /v1/phase3/baselines/{baseline_id}
```

### Drift

**List Drift Events**
```
GET /v1/phase3/drift?agent_id=support-agent&severity=high&resolved=false
```

**Get Drift Event**
```
GET /v1/phase3/drift/{drift_id}
```

**Drift Timeline**
```
GET /v1/phase3/drift/timeline?agent_id=support-agent&days=30
```

**Drift Summary**
```
GET /v1/phase3/drift/summary?environment=production&days=7
```

---

## Statistical Methods

### Chi-Square Test (Decision & Signal Distributions)

**Purpose:** Test if two categorical distributions differ significantly

**When Used:** Comparing decision distributions or signal distributions

**Formula:**
```
χ² = Σ [(O - E)² / E]
```
Where:
- O = Observed frequency
- E = Expected frequency (baseline)

**Interpretation:**
- p-value < 0.05 → Distributions differ significantly
- p-value ≥ 0.05 → No significant difference

**Example:**
```
Baseline: {api: 0.65, cache: 0.30, db: 0.05}
Observed: {api: 0.82, cache: 0.15, db: 0.03}

Chi-square test → p = 0.003 (significant!)
```

### Percent Threshold (Latency)

**Purpose:** Detect large percent changes in numeric metrics

**When Used:** Comparing latency statistics

**Formula:**
```
delta_percent = ((observed - baseline) / baseline) * 100
```

**Threshold:** >20% change = drift

**Example:**
```
Baseline P95: 2300ms
Observed P95: 3100ms
Delta: +35% → Drift detected!
```

### Severity Calculation

**Based purely on magnitude of change, not quality:**

- **Low:** ≤15% change
- **Medium:** 15-30% change
- **High:** >30% change

**Important:** Severity is informational, not judgmental.

---

## Configuration

Configuration file: `config/drift_thresholds.yaml`

### Default Thresholds

```yaml
decision_drift:
  p_value_threshold: 0.05
  min_delta_percent: 10.0

signal_drift:
  p_value_threshold: 0.05
  min_delta_percent: 15.0

latency_drift:
  min_delta_percent: 20.0

severity_thresholds:
  low:
    max_delta_percent: 15.0
  medium:
    max_delta_percent: 30.0

minimum_sample_sizes:
  profile: 100
  drift_detection: 50
```

### Environment Variables (Alerts)

```bash
# Slack integration
PHASE3_SLACK_ENABLED=true
PHASE3_SLACK_WEBHOOK_URL=https://hooks.slack.com/...
PHASE3_SLACK_CHANNEL=#agent-alerts

# PagerDuty integration
PHASE3_PAGERDUTY_ENABLED=false
PHASE3_PAGERDUTY_ROUTING_KEY=...

# Generic webhook
PHASE3_WEBHOOK_ENABLED=false
PHASE3_WEBHOOK_URL=https://...
```

---

## Usage Guide

### Step 1: Create a Baseline

```python
from backend.behavior_profiles import create_behavior_profile
from backend.baselines import create_baseline_from_profile
from datetime import datetime, timedelta

# 1. Build profile from historical data
window_end = datetime.utcnow()
window_start = window_end - timedelta(days=7)

profile_data = create_behavior_profile(
    db=db,
    agent_id="support-agent",
    agent_version="v1.0.0",
    environment="production",
    window_start=window_start,
    window_end=window_end,
    min_sample_size=100,
)

# 2. Create baseline from profile
baseline = create_baseline_from_profile(
    db=db,
    profile_id=profile_data["profile_id"],
    agent_id="support-agent",
    agent_version="v1.0.0",
    environment="production",
    baseline_type="version",
    approved_by="admin@example.com",
    description="Baseline for v1.0.0 production",
    auto_activate=True,
)

print(f"Baseline created: {baseline.baseline_id}")
```

### Step 2: Detect Drift

```python
from backend.drift_engine import detect_drift_for_baseline
from datetime import datetime, timedelta

# Run drift detection for last 24 hours
observed_end = datetime.utcnow()
observed_start = observed_end - timedelta(hours=24)

drift_events = detect_drift_for_baseline(
    db=db,
    baseline=baseline,
    observed_window_start=observed_start,
    observed_window_end=observed_end,
    min_sample_size=50,
    config_path="config/drift_thresholds.yaml",
)

print(f"Detected {len(drift_events)} drift events")

for drift in drift_events:
    print(f"  - {drift.metric}: {drift.delta_percent:+.1f}% (severity: {drift.severity})")
```

### Step 3: Emit Alerts

```python
from backend.alerts import emit_drift_alert

for drift in drift_events:
    emit_drift_alert(drift)
```

---

## Constraints & Guardrails

### Privacy Enforcement

**Database Trigger:**
```sql
-- Validates baseline descriptions contain no prompts/responses
CREATE TRIGGER trg_validate_baseline_description
BEFORE INSERT OR UPDATE ON behavior_baselines
FOR EACH ROW
EXECUTE FUNCTION validate_baseline_description();
```

**Forbidden Keywords:**
- prompt, response, reasoning, thought
- message, content, text, output, input
- chain_of_thought, explanation, rationale

### Immutability Enforcement

**Database Trigger:**
```sql
-- Prevents updates to baselines (except activation)
CREATE TRIGGER trg_prevent_baseline_update
BEFORE UPDATE ON behavior_baselines
FOR EACH ROW
EXECUTE FUNCTION prevent_baseline_update();
```

### Language Constraints

**Approved Phrases:**
- "Observed increase/decrease"
- "Distribution shifted"
- "Correlates with"
- "Detected deviation"

**Forbidden Phrases:**
- "Better/worse"
- "Correct/incorrect"
- "Optimal/suboptimal"
- "Fix this"
- "Agent should..."
- "Degraded/improved"

---

## Examples

### Example 1: Tool Selection Drift

**Scenario:** Agent starts using API more than cache

**Baseline:**
```
tool_selection: {api: 0.65, cache: 0.30, db: 0.05}
```

**Observed:**
```
tool_selection: {api: 0.82, cache: 0.15, db: 0.03}
```

**Drift Detected:**
```
Metric: tool_selection.api
Baseline: 65%
Observed: 82%
Delta: +17% (+26.15%)
Severity: medium
Significance: p=0.003 (Chi-square)
```

**Alert Message:**
```
Behavioral drift detected

Agent: support-agent v1.0.0 (production)
Metric: tool_selection.api
Change: observed increase from 65.00% to 82.00% (+26.2%)
Severity: medium

Baseline: abc123-def456-...
Statistical significance: p=0.0030
Test method: chi_square
Detected: 2026-01-02 14:30:00 UTC

Observation window: 2026-01-01 00:00 to 2026-01-02 23:59 (456 runs)
```

### Example 2: Latency Drift

**Scenario:** P95 latency increased significantly

**Baseline:**
```
p95_run_duration_ms: 2300
```

**Observed:**
```
p95_run_duration_ms: 3100
```

**Drift Detected:**
```
Metric: p95_run_duration_ms
Baseline: 2300ms
Observed: 3100ms
Delta: +800ms (+34.78%)
Severity: high
Test method: percent_threshold
```

### Example 3: Quality Signal Drift

**Scenario:** Schema validation failures increased

**Baseline:**
```
schema_valid: {full_match: 0.92, partial_match: 0.06, no_match: 0.02}
```

**Observed:**
```
schema_valid: {full_match: 0.84, partial_match: 0.08, no_match: 0.08}
```

**Drift Detected:**
```
Metric: schema_valid.no_match
Baseline: 2%
Observed: 8%
Delta: +6% (+300%)
Severity: high
Significance: p=0.001 (Chi-square)
```

---

## Troubleshooting

### Insufficient Data Error

**Error:** `InsufficientDataError: 45 runs found, minimum 100 required`

**Solution:** Wait for more data or reduce `min_sample_size`:
```python
profile = build_profile(..., min_sample_size=30)
```

### No Drift Detected (But Expected)

**Possible Causes:**
1. Thresholds too strict (reduce `min_delta_percent`)
2. Sample size too small (increase observation window)
3. Change is gradual (not statistically significant yet)

**Solution:** Tune thresholds in `config/drift_thresholds.yaml`

### Too Many Drift Alerts

**Possible Causes:**
1. Thresholds too sensitive
2. Normal behavior variation
3. Baseline needs updating

**Solution:**
1. Increase `min_delta_percent` thresholds
2. Create new baseline if behavior legitimately changed

---

## Best Practices

1. **Start with defaults** - Monitor alert volume before tuning
2. **Create version-based baselines** - One per stable version
3. **Review drift weekly** - Not all drift requires action
4. **Update baselines intentionally** - After verified changes
5. **Don't over-alert** - Higher thresholds = more actionable alerts
6. **Document baseline approvals** - Use description field
7. **Investigate high-severity drift first** - Prioritize by magnitude
8. **Remember: drift ≠ broken** - Drift is informational

---

## Migration from Phase 2

Phase 3 is **additive** - no changes to Phase 2 required.

**Existing Phase 2 agents work unchanged:**
- Phase 2 data continues to be collected
- Phase 3 reads Phase 2 data (read-only)
- No impact on Phase 1 or Phase 2 performance

**To enable Phase 3:**
1. Run migration: `003_phase3_behavior.sql`
2. Create baselines for existing agents
3. Enable drift detection (periodic job)
4. Configure alerts (optional)

---

## Future Enhancements

Potential additions in Phase 4+:

- Multi-baseline comparison
- Seasonal behavior modeling
- User-defined drift metrics
- Automated baseline rotation
- Drift resolution tracking
- Decision tree visualization
- Agent-specific thresholds

---

## Summary

**Phase 3 provides:**
- ✅ Behavioral baseline creation
- ✅ Statistical drift detection
- ✅ Informational alerts
- ✅ Neutral, observational language
- ✅ Privacy-safe analytics

**Phase 3 does NOT:**
- ❌ Judge agent quality
- ❌ Modify agent behavior
- ❌ Prescribe actions
- ❌ Create health scores
- ❌ Rank agents

**Remember:**
> "Phase 3 helps humans notice change — not decide what to do about it."

---

**Complete Phase 3 implementation available at:**
- Database: `db/migrations/003_phase3_behavior.sql`
- Backend: `backend/{behavior_profiles,baselines,drift_engine,alerts,query_phase3}.py`
- Config: `config/drift_thresholds.yaml`
- API: `GET /v1/phase3/*`
