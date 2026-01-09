# AI Assistant Guidelines for Drift Detection Development

## Purpose

This document defines **how AI coding assistants (like Claude Code)** should work on the drift detection capability of the AgentTracer platform.

Drift detection is **analysis-only**, **read-only**, and **non-interventional**.

AI assistants are permitted to:

- Assist with derivation logic
- Generate queries
- Create visualization logic
- Help reason about statistical drift

AI assistants are **not permitted** to:

- Invent agent behavior
- Suggest agent fixes
- Introduce control loops
- Infer reasoning or intent

## Core Rule (Non-Negotiable)

> **AI assistants may only help observe and describe agent behavior — never influence, evaluate, or optimize it.**

If an AI-generated change:

- Modifies agent execution
- Prescribes actions
- Judges correctness
- Introduces feedback loops

→ **Reject the change.**

## Allowed Work Areas

AI assistants **may assist with**:

### Drift Detection

- Drift detection logic
- Baseline comparison algorithms
- Statistical aggregation
- Trend analysis
- Visualization components
- Alert threshold definitions
- Read-only APIs
- Derived data models
- Documentation

### Forbidden Areas

- Prompt engineering
- Agent logic
- Retry policies
- Tool selection logic
- Auto-remediation
- Quality scoring
- "Health" metrics
- Agent ranking
- Recommendations or fixes

## Data Access Rules

AI assistants **must assume**:

- No access to prompts
- No access to responses
- No access to reasoning text
- No access to user input
- No access to retrieved documents

All drift detection inputs are:

- Aggregated
- Structured
- Privacy-safe
- Derived from decision and quality data only

If an AI assistant proposes accessing raw data → **invalid**.

## Mental Model AI Assistants Must Follow

AI assistants must reason using this pipeline only:

```
Decision & quality data
    ↓
Historical baseline
    ↓
Observed distribution
    ↓
Statistical comparison
    ↓
Drift signal
```

AI assistants **must not** introduce:

- Causal claims
- Optimization logic
- Decision enforcement

Only **observed change** is allowed.

## Drift Semantics (Strict)

AI assistants must treat "drift" as:

> A statistically significant change in a distribution relative to a baseline.

AI assistants **must not** equate drift with:

- failure
- bug
- regression
- correctness
- quality

Drift is **descriptive**, not evaluative.

## Language Constraints (Very Important)

AI assistants must use **neutral, observational language only**.

### Approved Language

- "Observed increase"
- "Distribution shifted"
- "Correlates with"
- "Detected deviation"
- "Baseline comparison shows"

### Forbidden Language

- "Better / Worse"
- "Correct / Incorrect"
- "Optimal / Suboptimal"
- "Fix this"
- "Agent should"
- "Improve performance"

If an AI assistant outputs judgmental language → **rewrite required**.

## Alerts & Notifications

AI assistants may help design alerts **only if**:

- Alerts are informational
- Alerts describe what changed
- Alerts reference the baseline
- Alerts do not prescribe actions

AI assistants must never suggest:

- automatic rollback
- retry tuning
- logic changes
- human instructions

## Code Generation Rules

AI-generated code **must**:

- Be read-only with respect to core telemetry data
- Use explicit typing
- Include docstrings
- Avoid side effects
- Be deterministic
- Avoid hidden heuristics

AI-generated code **must not**:

- Write to agent tables
- Modify agent state
- Call agent SDKs
- Trigger workflows

## Statistical Discipline

AI assistants may propose:

- KS tests
- Chi-square tests
- Jensen–Shannon divergence
- Percent delta thresholds
- Time-window comparisons

AI assistants **must**:

- Explain assumptions
- Avoid overfitting
- Avoid "magic thresholds"
- Allow human override

## UI & Visualization Rules

AI assistants may help generate:

- Charts
- Tables
- Dashboards

But must ensure:

- No single "health score"
- No rankings
- No recommendations
- No prescriptive annotations

Visuals must be:

- Comparative
- Time-based
- Distribution-oriented

## Failure Scenarios AI Assistants Must Anticipate

AI assistants should proactively consider:

- Sparse data
- Cold start baselines
- Seasonal behavior
- Legitimate behavior changes
- Version rollouts

AI assistants **must not** assume drift = problem.

## Human-in-the-Loop Boundary

AI assistant responsibility ends at **visibility**.

AI assistants must never:

- decide action
- suggest fixes
- automate responses

All interpretation belongs to humans.

## Review Checklist for AI-Generated Output

Before accepting AI-generated changes, verify:

- No agent behavior modification
- No privacy boundary violations
- No evaluative language
- No feedback loops
- No optimization logic
- Core telemetry data untouched
- Purely additive changes
- Observational semantics preserved

If any check fails → **reject**.

## File Structure Context

When working on drift detection code, AI assistants should reference these file paths:

**Backend (server/):**
- server/api/ingest.py - Write-only ingest API
- server/api/query.py - Read-only query API
- server/api/routers/drift.py - Drift query API router
- server/models/database.py - Data models
- server/core/behavior_profiles.py - Profile builder
- server/core/baselines.py - Baseline management
- server/core/drift_engine.py - Drift detection engine
- server/core/alerts.py - Alert emission

**Database:**
- server/db/schema.sql - Database schema
- server/db/migrations/ - Schema migrations

**SDK:**
- sdk/agenttrace.py - Client SDK (read-only reference)

**Tests:**
- tests/test_integration.py - Integration tests
- tests/test_decision_quality_validation.py - Decision/quality tests

## One-Line Rule for AI Assistants

> **AI assistants help humans notice change — not decide what to do about it.**

## Status

Drift detection is complete and production-ready (January 2026). These guidelines remain for maintenance and enhancements.
