# AgentTracer - Phase 1, 2 & 3 Complete

## Overview

This repository contains the **AgentTracer Platform** with Phases 1, 2, and 3 complete. AgentTracer offers **structured, privacy-safe observability for AI agents** by capturing:

**Phase 1: Execution Observability**
- Agent runs, ordered execution steps, and semantic failure details
- Step-level latency tracking and retry modeling

**Phase 2: Decision & Quality Observability**
- Agent decision points with structured reasoning
- Quality signals correlated with outcomes
- Observational analytics (no behavior modification)

**Phase 3: Behavioral Drift Detection** ✨ NEW
- Statistical baseline creation from historical behavior
- Drift detection via Chi-square tests and statistical comparison
- Informational alerts when behavior changes significantly
- Purely observational (drift ≠ bad, just describes change)

## What is this?

**AgentTracer** is an observability platform for AI agents. It records:

**Phase 1 (Execution):**
- Each agent execution ("run")
- The ordered sequence of steps within that run
- Step-level latency
- Retries as first-class events
- Semantic failure classifications

**Phase 2 (Decisions & Quality):**
- Agent decision points (tool selection, retry strategy, etc.)
- Structured reason codes (enum-based, privacy-safe)
- Quality signals (schema validation, tool success/failure, etc.)
- Confidence scores for decisions

**Phase 3 (Behavioral Drift):**
- Behavioral baselines (statistical snapshots of expected behavior)
- Drift detection (Chi-square tests, percent thresholds)
- Informational alerts (neutral language, no prescriptive actions)
- Drift timeline visualization

It allows engineers to **reconstruct and inspect agent behavior in production environments**, **understand why agents make specific choices**, and **detect when behavior changes significantly over time**.

## What problem does it solve?

AI agents can fail in ways that traditional observability tools do not explain:

- tools time out or return malformed data
- retries inflate latency without visibility
- retrieval returns no results
- agent behavior changes across versions without infrastructure changes
- failures are semantic rather than infrastructural

Existing tools, such as logs, metrics, and traces, indicate **what was executed**, but not **why an agent behaved as it did**. AgentTracer helps engineers to:

- identify where an agent failed
- understand which step caused the failure
- attribute latency to specific agent actions
- compare behavior across agent versions

## Who is this for?

AgentTracer is intended for:

- engineers operating LLM-based agents in production
- platform teams responsible for agent reliability
- teams integrating tools, retrieval, and orchestration with agents
- organizations that require privacy-safe observability

AgentTracer is also suitable for:

- backend engineers
- infra / platform engineers
- Applied AI / ML engineers

## Who is this not for?

AgentTracer is **not** intended for:

- prompt engineering workflows
- chat transcript storage
- prompt versioning or diffing
- model training or fine-tuning
- automatic agent optimization
- reinforcement learning pipelines
- evaluation benchmarks or grading frameworks

These areas are **explicitly out of scope** for AgentTracer. Phase 2 adds observational analytics but maintains strict boundaries against optimization and evaluation.

## Why does this exist?

AI agents are **non-deterministic, tool-driven systems**. Traditional observability assumes:

- deterministic code paths
- known failure modes

Agents violate these assumptions:

- decisions emerge from model inference
- failures are often semantic
- identical inputs may produce different behaviors
- latency is influenced by reasoning and retries

AgentTracer is designed to **make agent behavior inspectable** while maintaining safety and privacy.

## Core mental model

AgentTracer is built around a **minimal, explicit execution model**:

```
AgentRun
├─ AgentStep (ordered, Phase 1)
├─ AgentFailure (optional, Phase 1)
├─ AgentDecision (optional, Phase 2)
└─ AgentQualitySignal (optional, Phase 2)
     ↓
Phase 3 (Derived Analytics)
├─ BehaviorProfile (statistical snapshot)
├─ BehaviorBaseline (immutable baseline)
└─ BehaviorDrift (detected changes)
```

**Phase 1:**
- **AgentRun** represents a single execution attempt
- **AgentStep** represents one action taken by the agent
- **AgentFailure** represents the semantic reason a run failed

**Phase 2 (Additive):**
- **AgentDecision** represents a decision point with structured reasoning
- **AgentQualitySignal** represents an observable quality indicator

**Phase 3 (Derived Analytics):**
- **BehaviorProfile** aggregates Phase 2 data into statistical snapshot
- **BehaviorBaseline** represents immutable expected behavior
- **BehaviorDrift** records statistically significant behavioral changes

This model is **stable, intentionally constrained, and backward compatible.**

## Main concepts

### AgentRun

A single execution of an agent, identified by:

- agent ID
- agent version
- environment
- start and end timestamps
- final status (success / failure / partial)

### AgentStep

An ordered step within an agent run, such as:

- planning
- retrieval
- tool invocation
- response generation

Each step records:

- execution order (seq)
- latency
- step type
- safe metadata only

Retries are represented as **separate steps rather than** overwritten attempts.

### AgentFailure (Phase 1)

A structured, semantic failure description:

- failure type (tool / model / retrieval / orchestration)
- failure code (e.g., timeout, schema_invalid)
- optional linkage to the step that caused the failure

### AgentDecision (Phase 2)

A structured record of a decision point where the agent selected between options:

- decision type (tool_selection, retry_strategy, response_mode, etc.)
- selected option
- structured reason code (enum-based)
- candidates considered
- optional confidence score (0.0-1.0)

Example: "Selected 'api' over 'cache' because 'fresh_data_required' (confidence: 0.85)"

### AgentQualitySignal (Phase 2)

An atomic, factual signal correlated with outcome quality:

- signal type (schema_valid, tool_success, latency_threshold, etc.)
- signal code (specific indicator)
- boolean value (true/false)
- optional weight (importance)

Example: "Schema validation = full_match (true)" or "Tool execution = rate_limited (true)"

**Important:** Phase 2 is observational only - no quality scores or correctness judgments.

### BehaviorProfile (Phase 3)

A statistical snapshot of agent behavior over a time window, aggregated from Phase 2 data:

- decision distributions (e.g., tool_selection: {api: 0.65, cache: 0.30})
- signal distributions (e.g., schema_valid: {full_match: 0.92, partial_match: 0.06})
- latency statistics (mean, p50, p95, p99)
- sample size (number of runs aggregated)

Profiles are used to create baselines.

### BehaviorBaseline (Phase 3)

An immutable snapshot of expected agent behavior:

- baseline type (version-based, time-window, or manual)
- references a behavior profile
- optional human approval
- only one active baseline per (agent, version, environment)

Baselines cannot be modified after creation - ensures auditability and prevents silent baseline shifts.

### BehaviorDrift (Phase 3)

A record of statistically significant behavioral change:

- drift type (decision, signal, or latency)
- metric (specific dimension that changed)
- baseline vs observed values
- statistical significance (p-value)
- severity (low/medium/high based on magnitude)

**Critical:** Drift is **descriptive, not evaluative**. Drift means "behavior changed" - NOT "agent broke" or "quality degraded". Human interpretation required.

## Minimal usage

### Instrumenting an agent (Python)

```python
from sdk.agenttrace import AgentTracer

tracer = AgentTracer(
    agent_id="support-agent",
    agent_version="v1.0.0",
    environment="production",
    api_url="http://localhost:8000"
)

with tracer.start_run() as run:
    with run.step("plan", "analyze_query"):
        # Your planning logic
        pass

    with run.step("tool", "billing_api"):
        # Tool call logic
        pass

    with run.step("respond", "generate_response"):
        # Response generation
        pass
```

- No changes to prompts are required
- No model-specific logic is introduced

### Handling failures

```python
with tracer.start_run() as run:
    with run.step("plan", "analyze"):
        pass

    try:
        with run.step("tool", "external_api"):
            result = call_external_api()
    except TimeoutError:
        run.record_failure(
            failure_type="tool",
            failure_code="timeout",
            message="External API timeout after 30s"
        )
        return
```

## Where does this fit in a system

AgentTracer operates **alongside the agent runtime**:

```
Client
  ↓
Agent (LLM + Tools + Orchestration)
  ↓
AgentTracer SDK (this repository)
  ↓
Ingest API
  ↓
Observability Database
  ↓
Query API / UI
```

AgentTracer **observes execution** but does **not influence agent behavior**.

## Quick Start

### 1. Start the platform

```bash
# Clone the repository
git clone <repository-url>
cd testing

# Start all services with Docker Compose
docker compose up -d

# Verify services are running
curl http://localhost:8000/health  # Ingest API
curl http://localhost:8001/health  # Query API
```

### 2. Run example agent

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run example with instrumentation
PYTHONPATH=. python examples/customer_support_agent.py
```

### 3. View telemetry

```bash
# Query runs via API
curl http://localhost:8001/v1/runs | jq

# Get statistics
curl http://localhost:8001/v1/stats | jq

# Or view in UI (if running)
open http://localhost:3000
```

See [QUICK_START.md](./QUICK_START.md) for detailed instructions.

## Architecture

The platform consists of:

- **Ingest API** (port 8000): Write-only API for telemetry ingestion
- **Query API** (port 8001): Read-only API for querying runs
- **PostgreSQL**: Persistent storage with schema validation
- **Python SDK**: Client library for instrumenting agents
- **React UI**: Dashboard for visualizing runs and failures

See [docs/architecture.md](./docs/architecture.md) for detailed architecture documentation.

## Privacy-first design

AgentTracer enforces privacy at multiple layers:

**Never stored:**
- ❌ Raw prompts
- ❌ LLM responses
- ❌ Chain-of-thought
- ❌ User input
- ❌ Retrieved documents
- ❌ PII

**Always stored:**
- ✅ Step types and names
- ✅ Latency measurements
- ✅ Failure classifications
- ✅ Safe metadata (tool names, HTTP codes, counts)

Privacy is enforced through:
1. SDK-level metadata filtering
2. Pydantic validation with field validators
3. Database schema design (no TEXT columns for content)

See [docs/data-flow.md](./docs/data-flow.md) for privacy enforcement details.

## What this intentionally does NOT do

Phase 1 intentionally excludes:

- storage of prompts or LLM outputs
- chain-of-thought capture
- correctness evaluation
- replay or simulation
- agent self-modification
- automated optimization

These exclusions are intentional **design decisions**, not missing features.

## How does this differ from existing tools?

| Tool Type | Limitation | AgentTracer Approach |
|-----------|-----------|---------------------|
| **Logs** | Unstructured, difficult to aggregate | Structured runs with ordered steps |
| **Metrics** | No per-run context | Full run reconstruction with steps |
| **Traces** | Execution visibility without semantic meaning | Semantic failure taxonomy |
| **Prompt tools** | Text-focused, not runtime-focused | Privacy-safe execution observability |

AgentTracer introduces:

- agent-native execution primitives
- semantic failure classification
- explicit retry modeling
- privacy-first telemetry

## Documentation

Comprehensive documentation available in [docs/](./docs/):

- [Architecture](./docs/architecture.md) - System components and design
- [Data Flow](./docs/data-flow.md) - How telemetry flows through the system
- [Failure Handling](./docs/failure-handling.md) - Failure taxonomy and classification
- [Phase 2 Observability](./docs/phase2-observability.md) - Decision tracking and quality signals
- [Phase 3 Drift Detection](./docs/phase3-drift-detection.md) - Behavioral baselines and drift detection
- [Deployment](./docs/deployment.md) - Docker architecture and deployment
- [API Sequences](./docs/api-sequences.md) - Detailed API interactions
- [Component Responsibilities](./docs/component-responsibility.md) - Separation of concerns

## Examples

Two complete examples are provided:

1. **customer_support_agent.py** - Success case with retries
2. **agent_with_failures.py** - Demonstrates all failure types

Run examples:
```bash
# Phase 1 examples
PYTHONPATH=. python examples/customer_support_agent.py
PYTHONPATH=. python examples/agent_with_failures.py

# Phase 2 examples (includes decisions and quality signals)
PYTHONPATH=. python examples/agent_with_phase2.py
```

## Stability and maturity

**Phase 1, 2 & 3 status: Complete and production-ready.**

- Phase 1 data schema is stable (runs, steps, failures)
- Phase 2 data schema is stable (decisions, quality signals)
- Phase 3 data schema is stable (profiles, baselines, drift)
- SDK API is stable (backward compatible)
- Ingest and query APIs are stable
- Phase 3 query API complete (/v1/phase3/*)
- Drift detection engine operational

All phases are **additive** - no modifications to previous phases. Breaking changes to Phase 1, 2, or 3 primitives are **not anticipated.**

## Project scope summary

**What AgentTracer provides:**

**Phase 1:**
- Execution visibility
- Latency attribution
- Failure understanding

**Phase 2:**
- Decision observability
- Quality signal capture
- Structured reasoning codes

**Phase 3:**
- Behavioral baseline creation
- Statistical drift detection
- Informational alerts
- Drift timeline visualization

**What it does NOT do:**
- Judge correctness or quality
- Optimize decisions
- Change agent behavior
- Provide health scores or rankings
- Tune or evaluate agents
- Prescribe actions (alerts are informational only)

These boundaries are **strictly enforced** across all phases.

## Phase 2 Completion

Phase 2 has been successfully completed! See [PHASE2_COMPLETION_SUMMARY.md](./PHASE2_COMPLETION_SUMMARY.md) for:
- Complete feature list
- Implementation details
- Testing results
- Documentation links

For Phase 2 usage guide, see [docs/phase2-observability.md](./docs/phase2-observability.md).

## Phase 3 Completion

Phase 3 has been successfully completed! See [docs/phase3-drift-detection.md](./docs/phase3-drift-detection.md) for:
- Complete architecture and data models
- Statistical methods (Chi-square, percent thresholds)
- API reference (/v1/phase3/*)
- Configuration and thresholds
- Usage examples and best practices

**Key Features Delivered:**
- ✅ BehaviorProfileBuilder - Aggregates Phase 2 data into statistical profiles
- ✅ BaselineManager - Creates and manages immutable baselines
- ✅ DriftDetectionEngine - Detects behavioral changes via statistical comparison
- ✅ AlertEmitter - Emits neutral, informational alerts
- ✅ Query API - Read-only endpoints for profiles, baselines, and drift
- ✅ Configuration - Tunable thresholds in config/drift_thresholds.yaml
- ✅ Comprehensive Documentation - Complete guide with examples

**Design Principles Enforced:**
- Observational only (drift ≠ bad, just describes change)
- Neutral language ("observed increase", not "degraded")
- Statistical rigor (Chi-square tests, not heuristics)
- Human-in-the-loop (humans decide actions, not the system)
- Privacy-safe (derives from Phase 2, no prompts/responses)

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL 15
- **Statistics**: NumPy, SciPy (Phase 3 drift detection)
- **UI**: React 18, TypeScript, Tailwind CSS, Vite
- **Deployment**: Docker, Docker Compose
- **SDK**: Python with httpx

## License and contribution

This project is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.

For contribution guidelines, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## Closing note

AgentTracer prioritizes **clarity, safety, and correctness** over breadth of features.

> **Understanding agent behavior is a prerequisite to improving it.**

---

Built with [Claude Code](https://claude.com/claude-code)
