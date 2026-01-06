# AgentTracer Platform

## Overview

**AgentTracer** is a **privacy-safe observability platform for AI agents** that provides comprehensive behavioral monitoring through three integrated capabilities:

**Execution Observability**
- Agent runs, ordered execution steps, and semantic failure details
- Step-level latency tracking and retry modeling

**Decision & Quality Observability**
- Agent decision points with structured reasoning
- Quality signals correlated with outcomes
- Observational analytics (no behavior modification)

**Behavioral Drift Detection**
- Statistical baseline creation from historical behavior
- Drift detection via Chi-square tests and statistical comparison
- Informational alerts when behavior changes significantly
- Purely observational (drift ≠ bad, just describes change)

## What is this?

**AgentTracer** is an observability platform for AI agents. It records:

**Execution Tracking:**
- Each agent execution ("run")
- The ordered sequence of steps within that run
- Step-level latency
- Retries as first-class events
- Semantic failure classifications

**Behavioral Analysis:**
- Agent decision points (tool selection, retry strategy, etc.)
- Structured reason codes (enum-based, privacy-safe)
- Quality signals (schema validation, tool success/failure, etc.)
- Confidence scores for decisions

**Drift Detection:**
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

These areas are **explicitly out of scope** for AgentTracer. The platform provides observational analytics but maintains strict boundaries against optimization and evaluation.

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
├─ AgentStep (ordered execution steps)
├─ AgentFailure (optional semantic failure)
├─ AgentDecision (optional decision points)
└─ AgentQualitySignal (optional quality indicators)
     ↓
Derived Analytics
├─ BehaviorProfile (statistical snapshot)
├─ BehaviorBaseline (immutable baseline)
└─ BehaviorDrift (detected changes)
```

**Core Tracking:**
- **AgentRun** represents a single execution attempt
- **AgentStep** represents one action taken by the agent
- **AgentFailure** represents the semantic reason a run failed

**Behavioral Observability (Additive):**
- **AgentDecision** represents a decision point with structured reasoning
- **AgentQualitySignal** represents an observable quality indicator

**Derived Analytics:**
- **BehaviorProfile** aggregates behavioral data into statistical snapshots
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

### AgentFailure

A structured, semantic failure description:

- failure type (tool / model / retrieval / orchestration)
- failure code (e.g., timeout, schema_invalid)
- optional linkage to the step that caused the failure

### AgentDecision

A structured record of a decision point where the agent selected between options:

- decision type (tool_selection, retry_strategy, response_mode, etc.)
- selected option
- structured reason code (enum-based)
- candidates considered
- optional confidence score (0.0-1.0)

Example: "Selected 'api' over 'cache' because 'fresh_data_required' (confidence: 0.85)"

### AgentQualitySignal

An atomic, factual signal correlated with outcome quality:

- signal type (schema_valid, tool_success, latency_threshold, etc.)
- signal code (specific indicator)
- boolean value (true/false)
- optional weight (importance)

Example: "Schema validation = full_match (true)" or "Tool execution = rate_limited (true)"

**Important:** Quality signals are observational only - no quality scores or correctness judgments.

### BehaviorProfile

A statistical snapshot of agent behavior over a time window, aggregated from behavioral data:

- decision distributions (e.g., tool_selection: {api: 0.65, cache: 0.30})
- signal distributions (e.g., schema_valid: {full_match: 0.92, partial_match: 0.06})
- latency statistics (mean, p50, p95, p99)
- sample size (number of runs aggregated)

Profiles are used to create baselines.

### BehaviorBaseline

An immutable snapshot of expected agent behavior:

- baseline type (version-based, time-window, or manual)
- references a behavior profile
- optional human approval
- only one active baseline per (agent, version, environment)

Baselines cannot be modified after creation - ensures auditability and prevents silent baseline shifts.

### BehaviorDrift

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
# Install Python dependencies (recommended: uv)
uv pip install -e .
# Or using pip: pip install -e .

# Run example with instrumentation
python examples/customer_support_agent.py
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

AgentTracer intentionally excludes:

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

See [QUICK_START.md](./QUICK_START.md) for detailed getting started guide.

Additional documentation available in [docs/](./docs/):
- Internal development notes in [docs/internal/](./docs/internal/)
- Design templates in [docs/templates/](./docs/templates/)

## Examples

Complete usage examples are provided in [examples/](./examples/):

1. **customer_support_agent.py** - Success case with retries
2. **agent_with_failures.py** - Demonstrates all failure types
3. **agent_with_decisions_example.py** - Includes decisions and quality signals
4. **drift_detection_example.py** - Demonstrates drift detection workflow

Run examples:
```bash
python examples/customer_support_agent.py
python examples/agent_with_failures.py
python examples/agent_with_decisions_example.py
python examples/drift_detection_example.py
```

## Stability and maturity

**Status: Complete and production-ready.**

- Data schemas are stable (runs, steps, failures, decisions, signals, profiles, baselines, drift)
- SDK API is stable (backward compatible)
- Ingest and query APIs are stable
- Drift detection API complete (/v1/drift/*)
- Drift detection engine operational

All capabilities are **additive** - new features don't modify existing schemas. Breaking changes to core primitives are **not anticipated.**

## Project scope summary

**What AgentTracer provides:**

**Execution Observability:**
- Execution visibility
- Latency attribution
- Failure understanding

**Behavioral Analysis:**
- Decision observability
- Quality signal capture
- Structured reasoning codes

**Drift Detection:**
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

These boundaries are **strictly enforced** across all capabilities.

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL 15
- **Statistics**: NumPy, SciPy (drift detection)
- **UI**: React 18, TypeScript, Tailwind CSS, Vite
- **Deployment**: Docker, Docker Compose
- **SDK**: Python with httpx
- **Package Management**: uv (modern Python package manager)

## License and contribution

This project is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.

For contribution guidelines, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## Closing note

AgentTracer prioritizes **clarity, safety, and correctness** over breadth of features.

> **Understanding agent behavior is a prerequisite to improving it.**

---

Built with [Claude Code](https://claude.com/claude-code)
